/**
 * The single owner of everything the client knows.
 *
 * Systems never fetch on their own and never invent a number: they call one of
 * these methods, the controller asks the twin, and every listener redraws from
 * the payload that came back. One source, so two props cannot drift apart.
 */

import { session, twinApi } from './client.js';
import type { Caption, Fork, ScenePayload, Verdict } from './client.js';

type Listener = () => void;

class TwinController {
  payload: ScenePayload | null = null;
  /** The action the policy engine put on hold for a hand gesture. */
  pending: Verdict | null = null;
  captions: Caption[] = [];
  offline = false;
  route = '';
  /** False while the route is only what the environment says it would be. */
  routeMeasured = true;
  account = '';
  private chased = new Set<string>();
  private joining: Promise<boolean> | null = null;
  private listeners = new Set<Listener>();

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private emit(): void {
    for (const listener of this.listeners) listener();
  }

  private adopt(scene: ScenePayload | undefined): void {
    if (scene) {
      this.payload = scene;
      this.chaseUnknown(scene);
    }
    this.offline = false;
    this.emit();
  }

  /**
   * An unknown payment is money whose fate nobody has confirmed. The table asks
   * the provider once per attempt rather than leaving that boat in the fog.
   */
  private chaseUnknown(scene: ScenePayload): void {
    for (const payment of scene.payments) {
      if (payment.state !== 'unknown') continue;
      const marker = `${payment.action_id}:${payment.attempt}`;
      if (this.chased.has(marker)) continue;
      this.chased.add(marker);
      void this.reconcile(payment.action_id);
    }
  }

  private async call<T>(run: () => Promise<T>, fallback: T): Promise<T> {
    try {
      return await run();
    } catch {
      this.offline = true;
      this.emit();
      return fallback;
    }
  }

  /**
   * Land on the world this browser was pointed at, if it was pointed at one.
   *
   * Nothing here signs anybody up. The device key rides on every request and the
   * twin opens the world behind it, so the table is there before any account is.
   * `?email=&password=` is the only text a headset can be handed, and it is the one
   * way to join a world that already belongs to somebody.
   */
  private async joinWorld(): Promise<void> {
    if (!this.account) this.account = session.name;
    const wanted = signedInFromUrl();
    if (!wanted) return;
    // Two systems boot at once, so joining is one shared promise, not two logins.
    this.joining ??= this.authenticate(wanted.email, wanted.password).finally(() => {
      this.joining = null;
    });
    await this.joining;
  }

  private async authenticate(email: string, password: string): Promise<boolean> {
    const account = await this.call(() => twinApi.login(email, password), null);
    if (!account) return false;
    session.set(account);
    this.account = account.name;
    return true;
  }

  async signIn(email: string, password: string): Promise<boolean> {
    if (!(await this.authenticate(email, password))) return false;
    await this.boot();
    return true;
  }

  /** Leaving revokes the token. The device still opens this table; only the name goes. */
  async signOut(): Promise<void> {
    if (session.token) await this.call(() => twinApi.logout(), null);
    session.set(null);
    this.account = '';
    this.payload = null;
    this.captions = [];
    this.emit();
  }

  async boot(): Promise<void> {
    await this.joinWorld();
    const [world, health, me] = await Promise.all([
      this.call(() => twinApi.world(), null as ScenePayload | null),
      this.call(() => twinApi.health(), null),
      this.call(() => twinApi.me(), null),
    ]);
    if (world) this.payload = world;
    // A world nobody has named yet is still somebody's table, and the twin is the
    // one that knows what to call it.
    if (me && !this.account) this.account = me.name;
    if (health) {
      this.route = health.route;
      this.routeMeasured = health.route_is_measured;
    }
    this.offline = !world;
    this.emit();
  }

  async scrub(day: number): Promise<void> {
    const result = await this.call(() => twinApi.scrub(day), null);
    if (result) this.adopt(result.scene);
  }

  /** Yanking a pipe out of the table grows a second miniature without it. */
  async pull(eventId: string, label: string): Promise<Fork | null> {
    const result = await this.call(() => twinApi.pull(eventId), null);
    if (!result) return null;
    this.adopt(result.scene);
    const fork = result.fork;
    this.say(
      'fork',
      `${label} is out. ${fork.delta.verdict}: ${dollars(fork.delta.cost_change_dollars)} in cost over the horizon.`,
      `branch-${fork.branch}`,
    );
    return fork;
  }

  async fork(label: string, cancelEventIds: string[] = [], shift: Record<string, number> = {}): Promise<void> {
    const args: Record<string, unknown> = { label, cancel_event_ids: cancelEventIds };
    if (Object.keys(shift).length > 0) args.shift = shift;
    const result = await this.call(() => twinApi.propose([{ tool: 'fork', args }]), null);
    if (result) this.adopt(result.scene);
  }

  async propose(verb: string, eventId: string, justification: string): Promise<Verdict | null> {
    const result = await this.call(
      () =>
        twinApi.propose([
          { tool: 'propose_action', args: { verb, event_id: eventId, justification } },
        ]),
      null,
    );
    if (!result) return null;
    this.adopt(result.scene);
    const first = result.results[0] as unknown as Verdict | undefined;
    this.pending = first && first.verdict === 'require_approval' ? first : null;
    if (first) this.say('policy', first.reason, first.action_id);
    return first ?? null;
  }

  async approve(actionId: string, gesture: string): Promise<string | null> {
    const result = await this.call(() => twinApi.approve(actionId, gesture), null);
    this.pending = null;
    if (!result) return null;
    this.say('approval', `Settled as ${result.state}.`, actionId);
    await this.refresh();
    return result.state;
  }

  async reconcile(actionId: string): Promise<void> {
    const result = await this.call(() => twinApi.reconcile(actionId), null);
    if (!result) return;
    this.say('reconcile', `Asked the provider about that one again. It is ${result.state}.`, actionId);
    await this.refresh();
  }

  /** A line the twin said in this app, in the same shape the heartbeat returns. */
  say(step: string, text: string, target = ''): void {
    if (!text) return;
    this.captions = [...this.captions.slice(-5), { step, text, target }];
    this.emit();
  }

  /**
   * The newest line, rewritten rather than stacked. A sentence that arrives in
   * pieces is one caption growing longer, not five captions.
   */
  private caption(step: string, text: string, target = ''): void {
    if (!text) return;
    const last = this.captions[this.captions.length - 1];
    this.captions = last && last.step === step
      ? [...this.captions.slice(0, -1), { step, text, target }]
      : [...this.captions.slice(-5), { step, text, target }];
    this.emit();
  }

  async tick(days: number, finalOfDay: boolean): Promise<Caption[]> {
    const result = await this.call(() => twinApi.tick(days, finalOfDay), null);
    if (!result) return [];
    this.captions = result.captions;
    this.adopt(result.scene);
    return result.captions;
  }

  /**
   * Ask, and let the answer arrive as it is phrased.
   *
   * Each piece the twin sends has already had its numbers checked, so growing the
   * caption sentence by sentence is safe. When the whole answer arrives the caption
   * is set from it rather than left as the sum of the pieces, because a stream that
   * froze mid-sentence ends with a different sentence than the one it started.
   */
  async ask(intent: string): Promise<string> {
    const pieces: string[] = [];
    const result = await this.call(
      () => twinApi.askStream(intent, (piece) => {
        pieces.push(piece);
        this.caption('answer', pieces.join(''));
      }),
      null,
    );
    if (!result) return pieces.join('');
    // Whichever endpoint answered is now known, not merely configured.
    if (result.route) {
      this.route = result.route;
      this.routeMeasured = true;
    }
    this.adopt(result.scene);
    this.caption('answer', result.said ?? '');
    return result.said ?? '';
  }

  async refresh(): Promise<void> {
    const result = await this.call(() => twinApi.world(), null);
    if (result) this.adopt(result);
  }
}

/** `?email=&password=` is the only text entry a headset has; use it to join an account. */
function signedInFromUrl(): { email: string; password: string } | null {
  const params = new URLSearchParams(location.search);
  const email = params.get('email');
  const password = params.get('password');
  return email && password ? { email, password } : null;
}

function dollars(value: number): string {
  const sign = value < 0 ? 'minus' : 'plus';
  return `${sign} $${Math.abs(value).toFixed(2)}`;
}

export const twin = new TwinController();
