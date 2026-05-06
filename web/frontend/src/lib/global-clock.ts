/**
 * Single shared "tick" clock for any UI that needs to update once per
 * ~250ms (currently: ThinkingBlock duration counters, possibly later:
 * relative-time labels, queued-task spinners).
 *
 * Why share one clock?
 *   Each ThinkingBlock used to start its own setInterval, so a long
 *   chat history with 50 thinking segments meant 50 timers all firing
 *   every 250ms — unnecessary CPU, especially while the user wasn't
 *   even looking at those collapsed blocks.
 *
 * Subscribe with onMounted, unsubscribe with onBeforeUnmount, read
 * `nowTick.value` like any other Vue ref.
 */
import { onBeforeUnmount, onMounted, ref } from "vue";

const TICK_MS = 250;

let timer: number | null = null;
let refCount = 0;

export const nowTick = ref(Date.now());

function start(): void {
  if (timer !== null) return;
  timer = window.setInterval(() => {
    nowTick.value = Date.now();
  }, TICK_MS);
}

function stop(): void {
  if (timer === null) return;
  window.clearInterval(timer);
  timer = null;
}

/**
 * Vue composable: keeps the global clock running for as long as your
 * component is mounted; tears it down once the last subscriber unmounts.
 */
export function useGlobalClock(): void {
  onMounted(() => {
    refCount += 1;
    if (refCount === 1) start();
    // Make sure the very next tick reflects now so freshly-mounted UIs
    // don't show a stale value for up to TICK_MS ms.
    nowTick.value = Date.now();
  });
  onBeforeUnmount(() => {
    refCount = Math.max(0, refCount - 1);
    if (refCount === 0) stop();
  });
}
