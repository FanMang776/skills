// 全局主题：深色科技风，黄绿高亮（延续账号视觉）
export const C = {
  bg: '#0d1117',
  panel: '#161b22',
  panel2: '#1c2129',
  border: '#30363d',
  text: '#e6edf3',
  muted: '#8b949e',
  accent: '#a3e635', // 黄绿高亮
  yellow: '#facc15',
  red: '#f87171',
  blue: '#58a6ff',
  orange: '#fb923c',
};

export const FPS = 30;

// TTS 实测时长（秒），来自 tts-durations.json
export const TTS = {
  p1: 10.416, p2: 19.32, p3: 27.0, p4: 32.688,
  p5: 34.272, p6: 37.848, p7: 20.136, p8: 18.192,
};

// 每场景 = 旁白时长 + 0.6s 收尾呼吸
export const sceneDur = (sec: number) => Math.ceil((sec + 0.6) * FPS);

// 各场景起始帧（顺序排列）
export const sceneStart = (() => {
  const ids = ['p1', 'p2', 'p3', 'p4', 'p5', 'p6', 'p7', 'p8'] as const;
  const starts: Record<string, number> = {};
  let acc = 0;
  for (const id of ids) {
    starts[id] = acc;
    acc += sceneDur(TTS[id]);
  }
  return starts;
})();

export const TOTAL_FRAMES = sceneStart.p8 + sceneDur(TTS.p8) + 90; // +3s 片尾定格
