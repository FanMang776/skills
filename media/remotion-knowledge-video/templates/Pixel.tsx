import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { C, GRID_W, GRID_H, SCALE, GROUND_Y } from '../theme';
import { F } from './Rich';

// ---------- 像素舞台:480×270 逻辑网格 ×4 到 1920×1080 ----------
export const PixelStage: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ backgroundColor: C.bg }}>
    <div
      style={{
        width: GRID_W,
        height: GRID_H,
        transform: `scale(${SCALE})`,
        transformOrigin: 'top left',
        position: 'absolute',
      }}
    >
      {children}
    </div>
  </AbsoluteFill>
);

// ---------- 基础像素矩形 ----------
export const R: React.FC<{ x: number; y: number; w: number; h: number; c: string }> = ({ x, y, w, h, c }) => (
  <div style={{ position: 'absolute', left: x, top: y, width: w, height: h, backgroundColor: c }} />
);

// ---------- 确定性伪随机(禁 Math.random) ----------
export const prand = (seed: number): number => {
  const x = Math.sin(seed * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

// ---------- 网格背景 + 像素光斑 + 渐晕 ----------
export const GridBg: React.FC<{ t: number }> = ({ t }) => {
  const dots: React.ReactNode[] = [];
  for (let gx = 0; gx < GRID_W; gx += 16)
    for (let gy = 0; gy < GRID_H; gy += 16)
      dots.push(<R key={`${gx}-${gy}`} x={gx} y={gy} w={1} h={1} c={C.grid} />);
  const glowX = 370 + Math.sin(t * 0.05) * 20;
  return (
    <>
      {dots}
      {/* 渐晕:左右暗边(逻辑系) */}
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at center, transparent 55%, rgba(4,8,14,0.55) 100%)' }} />
    </>
  );
};

// ---------- 地面 ----------
export const Ground: React.FC = () => (
  <>
    <R x={0} y={GROUND_Y} w={GRID_W} h={GRID_H - GROUND_Y} c={C.ground} />
    <R x={0} y={GROUND_Y} w={GRID_W} h={1} c={C.groundLine} />
  </>
);

// ---------- 集装箱(亮边/暗边立体感) ----------
export const Crate: React.FC<{ x: number; y: number; c: string }> = ({ x, y, c }) => (
  <>
    <R x={x} y={y} w={5} h={4} c={c} />
    <R x={x} y={y} w={5} h={1} c="rgba(255,255,255,0.27)" />
    <R x={x} y={y + 3} w={5} h={1} c="rgba(0,0,0,0.4)" />
    <R x={x} y={y} w={1} h={4} c="rgba(255,255,255,0.13)" />
    <R x={x + 4} y={y} w={1} h={4} c="rgba(0,0,0,0.33)" />
  </>
);

// ---------- Docker 鲸鱼(官方 logo 结构:双层箱 + 翘尾 + 喷水泡泡) ----------
export const Whale: React.FC<{ x: number; y: number; t: number; bubbles?: boolean }> = ({ x, y, t, bubbles = true }) => {
  const bob = t % 6 < 3 ? 0 : 1;
  const crates: React.ReactNode[] = [];
  for (let i = 0; i < 4; i++) crates.push(<Crate key={`b${i}`} x={x + 10 + i * 6} y={y - 4 + bob} c={i % 2 ? C.crateB : C.crateA} />);
  for (let i = 0; i < 3; i++) crates.push(<Crate key={`t${i}`} x={x + 13 + i * 6} y={y - 9 + bob} c={i % 2 ? C.crateA : C.crateB} />);
  const bt = t % 50;
  const bubs: React.ReactNode[] = [];
  if (bubbles && bt < 26) {
    for (let i = 0; i < 4; i++) {
      const by = y - 2 - (bt - i * 3);
      if (by > y - 30 && bt > i * 3) bubs.push(<R key={i} x={x + 3 + i * 2} y={by} w={1} h={1} c={C.bubble} />);
    }
  }
  return (
    <>
      {crates}
      {/* 身体:圆头长条 */}
      <R x={x + 2} y={y + bob} w={32} h={3} c={C.blue} />
      <R x={x} y={y + 3 + bob} w={36} h={4} c={C.blue} />
      <R x={x + 1} y={y + 7 + bob} w={33} h={1} c={C.blue} />
      {/* 腹部阴影 + 头部高光 */}
      <R x={x + 5} y={y + 6 + bob} w={26} h={2} c={C.blueDk} />
      <R x={x + 3} y={y + 1 + bob} w={8} h={1} c={C.blueLt} />
      {/* 眼睛 + 嘴 */}
      <R x={x + 3} y={y + 2 + bob} w={2} h={2} c={C.white} />
      <R x={x + 4} y={y + 3 + bob} w={1} h={1} c={C.dark} />
      <R x={x + 2} y={y + 5 + bob} w={3} h={1} c={C.blueDk} />
      {/* 尾巴两级翘起 + 圆润尾鳍 */}
      <R x={x + 32} y={y - 1 + bob} w={5} h={3} c={C.blue} />
      <R x={x + 36} y={y - 4 + bob} w={3} h={4} c={C.blue} />
      <R x={x + 35} y={y - 8 + bob} w={3} h={5} c={C.blue} />
      <R x={x + 40} y={y - 7 + bob} w={3} h={4} c={C.blue} />
      <R x={x + 38} y={y - 5 + bob} w={4} h={2} c={C.blue} />
      {bubs}
    </>
  );
};

// ---------- 马赛克小人(锚点 x=中心,y=脚底) ----------
// action: walk(4帧摆臂) / idle(呼吸+眨眼) / talk(说话开合) / point(前指)
export type GuyAction = 'walk' | 'idle' | 'talk' | 'point';
export const Guy: React.FC<{ x: number; y: number; t: number; facing?: number; action?: GuyAction }> = ({
  x, y, t, facing = 1, action = 'idle',
}) => {
  const dir = facing >= 0 ? 1 : -1;
  const X = (dx: number) => Math.round(x + dx * dir);
  const blink = t % 40 >= 38;
  const talking = action === 'talk';

  let bob = 0, legL = 0, legR = 0, armSwing = 0;
  if (action === 'walk') {
    const ph = t % 4;
    bob = ph % 2 === 0 ? 0 : 1;
    legL = ph === 0 ? 2 : ph === 2 ? -2 : 0;
    legR = ph === 2 ? 2 : ph === 0 ? -2 : 0;
    armSwing = ph === 0 ? -2 : ph === 2 ? 2 : 0;
  } else {
    bob = t % 8 < 4 ? 0 : 1;
  }

  return (
    <>
      {/* 腿 + 鞋 */}
      <R x={X(-4 + legL)} y={y - 6} w={3} h={6} c={C.dark} />
      <R x={X(1 + legR)} y={y - 6} w={3} h={6} c={C.dark} />
      <R x={X(-4 + legL)} y={y - 1} w={3} h={1} c={C.shoe} />
      <R x={X(1 + legR)} y={y - 1} w={3} h={1} c={C.shoe} />
      {/* 连帽衫身体 */}
      <R x={X(-5)} y={y - 15 + bob} w={10} h={9} c={C.blue} />
      <R x={X(-5)} y={y - 15 + bob} w={10} h={1} c={C.blueLt} />
      <R x={X(-5)} y={y - 7 + bob} w={10} h={1} c={C.blueDk} />
      <R x={X(-1)} y={y - 14 + bob} w={2} h={6} c={C.blueDk} />
      <R x={X(-3)} y={y - 9 + bob} w={2} h={1} c={C.blueDk} />
      <R x={X(1)} y={y - 9 + bob} w={2} h={1} c={C.blueDk} />
      {/* 手臂 */}
      {action === 'point' ? (
        <>
          <R x={X(4)} y={y - 14 + bob} w={5} h={2} c={C.blue} />
          <R x={X(9)} y={y - 14 + bob} w={1} h={2} c={C.skin} />
        </>
      ) : action === 'walk' ? (
        <>
          <R x={X(-7 + armSwing)} y={y - 14 + bob} w={2} h={5} c={C.blue} />
          <R x={X(5 - armSwing)} y={y - 14 + bob} w={2} h={5} c={C.blue} />
          <R x={X(-7 + armSwing)} y={y - 9 + bob} w={2} h={1} c={C.skin} />
          <R x={X(5 - armSwing)} y={y - 9 + bob} w={2} h={1} c={C.skin} />
        </>
      ) : (
        <>
          <R x={X(-7)} y={y - 14 + bob} w={2} h={6} c={C.blue} />
          <R x={X(5)} y={y - 14 + bob} w={2} h={6} c={C.blue} />
          <R x={X(-7)} y={y - 8 + bob} w={2} h={1} c={C.skin} />
          <R x={X(5)} y={y - 8 + bob} w={2} h={1} c={C.skin} />
        </>
      )}
      {/* 头:chibi 比例 + 刘海 + 呆毛 */}
      <R x={X(-4)} y={y - 24 + bob} w={9} h={9} c={C.skin} />
      <R x={X(-4)} y={y - 24 + bob} w={9} h={2} c={C.hair} />
      <R x={X(-4)} y={y - 22 + bob} w={2} h={2} c={C.hair} />
      <R x={X(3)} y={y - 22 + bob} w={2} h={1} c={C.hair} />
      <R x={X(-1)} y={y - 26 + bob} w={1} h={2} c={C.hair} />
      {/* 眼睛(竖眼/眨眼) */}
      {blink ? (
        <>
          <R x={X(-1)} y={y - 19 + bob} w={1} h={1} c={C.hair} />
          <R x={X(2)} y={y - 19 + bob} w={1} h={1} c={C.hair} />
        </>
      ) : (
        <>
          <R x={X(-1)} y={y - 20 + bob} w={1} h={2} c={C.dark} />
          <R x={X(2)} y={y - 20 + bob} w={1} h={2} c={C.dark} />
        </>
      )}
      {/* 腮红 + 嘴 */}
      <R x={X(-3)} y={y - 18 + bob} w={1} h={1} c={C.blush} />
      <R x={X(3)} y={y - 18 + bob} w={1} h={1} c={C.blush} />
      {talking ? (
        t % 2 === 0
          ? <R x={X(0)} y={y - 17 + bob} w={2} h={2} c={C.mouth} />
          : <R x={X(0)} y={y - 17 + bob} w={2} h={1} c={C.mouth} />
      ) : (
        <R x={X(0)} y={y - 17 + bob} w={2} h={1} c={C.mouth} />
      )}
    </>
  );
};

// ---------- 像素终端面板(lines 逐行出现,reveal: 打字机 0..1) ----------
export type TermLine = { text: string; color?: string; start?: number };
export const Terminal: React.FC<{ x: number; y: number; w: number; h: number; lines: TermLine[]; frame: number; title?: string }> = ({
  x, y, w, h, lines, frame, title,
}) => (
  <>
    <R x={x} y={y} w={w} h={h} c={C.terminalBg} />
    <R x={x} y={y} w={w} h={2} c={C.muted} />
    {title && (
      <div style={{ position: 'absolute', left: x + w - 4, top: y + 2, transform: 'translateX(-100%)', fontFamily: 'Consolas, "Courier New", monospace', fontSize: 5, color: C.muted }}>{title}</div>
    )}
    <R x={x + 8} y={y + 10} w={4} h={8} c={C.cyan} />
    {lines.map((ln, i) => {
      const start = ln.start ?? i * 12;
      if (frame < start) return null;
      const chars = Math.min(ln.text.length, Math.floor((frame - start) / 2));
      const shown = ln.text.slice(0, chars);
      return (
        <div key={i} style={{ position: 'absolute', left: x + 18, top: y + 9 + i * 12, fontFamily: 'Consolas, "Courier New", monospace', fontSize: 8, color: ln.color ?? C.white, whiteSpace: 'pre' }}>
          {shown}
        </div>
      );
    })}
  </>
);

// ---------- 像素字卡(标题揭示条) ----------
export const TitleCard: React.FC<{ y: number; text: string; frame: number; start?: number; w?: number }> = ({ y, text, frame, start = 0, w = 220 }) => {
  const f = frame - start;
  if (f < 0) return null;
  const reveal = Math.min(1, f / 20);
  return (
    <>
      <R x={(GRID_W - w) / 2} y={y} w={w} h={26} c="rgba(0,0,0,0.5)" />
      <R x={(GRID_W - w) / 2} y={y} w={Math.floor(w * reveal)} h={2} c={C.cyan} />
      <div style={{ position: 'absolute', left: GRID_W / 2, top: y + 5, transform: 'translateX(-50%)', fontFamily: F.body, fontWeight: 900, fontSize: 14, color: C.white, whiteSpace: 'nowrap' }}>
        {text}
      </div>
    </>
  );
};

// ---------- 像素标签(弹出式) ----------
export const Tag: React.FC<{ x: number; y: number; text: string; frame: number; start: number; c?: string }> = ({ x, y, text, frame, start, c = C.cyan }) => {
  if (frame < start) return null;
  const pop = Math.min(1, (frame - start) / 8);
  return (
    <div style={{ position: 'absolute', left: x, top: y, transform: `translateX(-50%) scale(${pop})`, fontFamily: F.body, fontWeight: 900, fontSize: 9, color: C.bg, backgroundColor: c, padding: '2px 6px', whiteSpace: 'nowrap' }}>
      {text}
    </div>
  );
};

// ---------- 场景时钟:30fps → 12fps 阶跃(像素动画节拍) ----------
export const useTick = (): number => Math.floor(useCurrentFrame() / 2.5);

// ---------- 节拍字卡:到帧弹出(画面跟口播逐句推进的基本单元) ----------
export const PopText: React.FC<{
  x: number; y: number; text: string; frame: number; start: number;
  color?: string; size?: number; bg?: string; bar?: boolean; center?: boolean;
}> = ({ x, y, text, frame, start, color = C.white, size = 9, bg = 'rgba(0,0,0,0.55)', bar = true, center = false }) => {
  if (frame < start) return null;
  const pop = Math.min(1, (frame - start) / 8);
  return (
    <div
      style={{
        position: 'absolute', left: x, top: y,
        transform: `${center ? 'translateX(-50%) ' : ''}scale(${pop})`,
        transformOrigin: center ? 'center top' : 'left top',
        fontFamily: 'Consolas, "Microsoft YaHei", monospace', fontWeight: 900,
        fontSize: size, color, backgroundColor: bg, padding: '3px 6px',
        borderTop: bar ? `2px solid ${C.cyan}` : 'none', whiteSpace: 'nowrap',
      }}
    >
      {text}
    </div>
  );
};

// ---------- 检查清单行(✓/✗状态) ----------
export const CheckRow: React.FC<{ x: number; y: number; label: string; state: 'todo' | 'ok' | 'fail'; frame: number; start: number }> = ({ x, y, label, state, frame, start }) => {
  if (frame < start) return null;
  const mark = state === 'ok' ? '✓' : state === 'fail' ? '✗' : '…';
  const mc = state === 'ok' ? C.cyan : state === 'fail' ? C.red : C.muted;
  return (
    <div style={{ position: 'absolute', left: x, top: y, fontFamily: 'Consolas, "Microsoft YaHei", monospace', fontSize: 9, color: state === 'todo' ? C.muted : C.white, whiteSpace: 'nowrap' }}>
      <span style={{ color: mc, fontWeight: 900 }}> {mark} </span>{label}
    </div>
  );
};
