// Type augmentations for browser APIs that aren't in TS's default lib targets.

interface WakeLockSentinel {
  release(): Promise<void>;
}

interface WakeLock {
  request(type: "screen"): Promise<WakeLockSentinel>;
}

interface Navigator {
  wakeLock?: WakeLock;
}

interface Window {
  webkitAudioContext?: typeof AudioContext;
}
