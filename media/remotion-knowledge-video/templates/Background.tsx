import React from 'react';
import { useCurrentFrame } from 'remotion';
import { C } from '../theme';

// 确定性伪随机（渲染必须可复现）
const prand = (i: number, salt = 1) =>
  (Math.sin(i * 127.1 + salt * 311.7) * 43758.5453) % 1;

// 背景层 v3：三层景深 bokeh 光斑 + 细网格 + 渐晕
// 光斑大而虚（近景）、小而实（远景），缓慢上浮，方向一致
export const Background: React.FC = () => {
  const frame = useCurrentFrame();
  const spots = Array.from({ length: 14 }).map((_, i) => {
    const depth = Math.abs(prand(i, 7)); // 0 远 1 近
    const x = Math.abs(prand(i, 1)) * 1080;
    const speed = 0.15 + depth * 0.5;
    const size = 8 + depth * 46;
    const y = 1980 - ((frame * speed + Math.abs(prand(i, 4)) * 2200) % 2300);
    const op = 0.05 + depth * 0.13;
    const warm = Math.abs(prand(i, 6)) > 0.8;
    return { x, y, size, op, color: warm ? C.yellow : C.accent, blur: 2 + (1 - depth) * 6 };
  });
  return (
    <div style={{ position: 'absolute', inset: 0, backgroundColor: C.bg, overflow: 'hidden' }}>
      {/* 细网格，几乎不可见 */}
      <div
        style={{
          position: 'absolute', inset: 0,
          backgroundImage: `linear-gradient(${C.border}18 1px, transparent 1px), linear-gradient(90deg, ${C.border}18 1px, transparent 1px)`,
          backgroundSize: '88px 88px',
          transform: `translateY(${(frame * 0.22) % 88}px)`,
        }}
      />
      {spots.map((s, i) => (
        <div
          key={i}
          style={{
            position: 'absolute', left: s.x, top: s.y,
            width: s.size, height: s.size, borderRadius: '50%',
            backgroundColor: s.color, opacity: s.op, filter: `blur(${s.blur}px)`,
          }}
        />
      ))}
      {/* 渐晕 */}
      <div
        style={{
          position: 'absolute', inset: 0,
          background: `radial-gradient(ellipse at 50% 36%, transparent 32%, ${C.bg} 105%)`,
        }}
      />
    </div>
  );
};
