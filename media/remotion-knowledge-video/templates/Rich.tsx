import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { C } from '../theme';
import { TypeText } from './Ui';

// 静态 @font-face 声明
export const FontFaces: React.FC = () => (
  <style>{`
    @font-face {
      font-family: 'SourceHan';
      src: url('/fonts/SourceHanSansSC-Heavy.otf') format('opentype');
      font-weight: 900;
    }
    @font-face {
      font-family: 'SourceHan';
      src: url('/fonts/SourceHanSansSC-Bold.otf') format('opentype');
      font-weight: 700;
    }
    @font-face {
      font-family: 'SourceHan';
      src: url('/fonts/SourceHanSansSC-Normal.otf') format('opentype');
      font-weight: 400;
    }
  `}</style>
);

// 全局字体 token
export const F = {
  display: "'SourceHan', 'Microsoft YaHei', sans-serif",
  body: "'SourceHan', 'Microsoft YaHei', sans-serif",
};

// ---------- 大标题 v4：clipPath 上下各留 20% 余量修裁字 bug ----------
export const DisplayTitle: React.FC<{
  text: string;
  showFrom: number;
  size?: number;
  color?: string;
  top: number;
  align?: 'center' | 'left';
  lineHeight?: number;
}> = ({ text, showFrom, size = 96, color = C.text, top, align = 'center', lineHeight = 1.25 }) => {
  const f = useCurrentFrame();
  if (f < showFrom) return null;
  const t = f - showFrom;
  const clip = interpolate(t, [0, 14], [0, 100], { extrapolateRight: 'clamp' });
  const rise = interpolate(t, [0, 14], [36, 0], { extrapolateRight: 'clamp' });
  const op = interpolate(t, [0, 8], [0, 1], { extrapolateRight: 'clamp' });
  // 修复裁字：inset 上下各留 20%，只从下缘揭示文字带
  const revealBand = interpolate(clip, [0, 100], [0, 80]); // 揭示带高度 0→80%
  return (
    <div
      style={{
        position: 'absolute', top, left: align === 'center' ? 0 : 90, right: align === 'center' ? 0 : 90,
        textAlign: align,
        fontFamily: F.display, fontWeight: 900, fontSize: size, letterSpacing: 2,
        color, lineHeight,
        clipPath: `inset(-20% 0 ${100 - revealBand - 20 < 0 ? 0 : 100 - revealBand - 20}% 0)`,
        transform: `translateY(${rise}px)`,
        opacity: op,
        textShadow: '0 2px 18px rgba(0,0,0,0.45)',
      }}
    >
      {text}
    </div>
  );
};

// ---------- 强调词：色块衬底 + 变色，代替发光 ----------
export const AccentChip: React.FC<{
  children: React.ReactNode;
  showFrom: number;
  color?: string;
}> = ({ children, showFrom, color = C.accent }) => {
  const f = useCurrentFrame();
  if (f < showFrom) return null;
  const t = f - showFrom;
  const w = interpolate(t, [0, 12], [0, 100], { extrapolateRight: 'clamp' });
  return (
    <span style={{ position: 'relative', display: 'inline-block' }}>
      <span
        style={{
          position: 'absolute', left: -6, right: -6, bottom: 6, height: '34%',
          backgroundColor: color, opacity: 0.16, borderRadius: 6,
          transformOrigin: 'left', transform: `scaleX(${w / 100})`,
        }}
      />
      <span style={{ position: 'relative', color }}>{children}</span>
    </span>
  );
};

// ---------- 玻璃面板 ----------
export const GlassPanel: React.FC<{
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ children, style }) => (
  <div
    style={{
      position: 'relative',
      backgroundColor: 'rgba(22,27,34,0.78)',
      backdropFilter: 'blur(24px)',
      border: '1px solid rgba(240,246,252,0.10)',
      borderRadius: 24,
      boxShadow: '0 24px 70px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.06)',
      overflow: 'hidden',
      ...style,
    }}
  >
    {children}
  </div>
);

// ---------- 扫光 ----------
export const ShineSweep: React.FC<{ showFrom: number; width?: number }> = ({ showFrom, width = 1080 }) => {
  const frame = useCurrentFrame();
  if (frame < showFrom) return null;
  const t = interpolate(frame, [showFrom, showFrom + 34], [-0.3, 1.3], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const op = interpolate(frame, [showFrom, showFrom + 10, showFrom + 26, showFrom + 34], [0, 0.45, 0.45, 0], {
    extrapolateLeft: 'clamp',
  });
  return (
    <div
      style={{
        position: 'absolute', top: -60, bottom: -60, width: 90,
        left: t * width,
        background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.16), transparent)',
        transform: 'skewX(-18deg)', opacity: op, pointerEvents: 'none',
      }}
    />
  );
};

// ---------- 环境光斑 ----------
export const AmbientGlow: React.FC<{
  x: number; y: number; size: number; color: string; opacity?: number;
}> = ({ x, y, size, color, opacity = 0.14 }) => {
  const frame = useCurrentFrame();
  const breathe = 1 + Math.sin(frame / 90) * 0.03;
  return (
    <div
      style={{
        position: 'absolute', left: x - size / 2, top: y - size / 2,
        width: size, height: size, borderRadius: '50%',
        background: `radial-gradient(circle, ${color}${Math.round(opacity * 255).toString(16).padStart(2, '0')} 0%, transparent 65%)`,
        transform: `scale(${breathe})`,
      }}
    />
  );
};

// ---------- 飞入 ----------
export const FlyIn: React.FC<{
  children: React.ReactNode;
  from?: 'left' | 'right' | 'bottom' | 'top';
  showFrom: number;
  distance?: number;
  style?: React.CSSProperties;
}> = ({ children, from = 'bottom', showFrom, distance = 60, style }) => {
  const frame = useCurrentFrame();
  if (frame < showFrom) return null;
  const p = interpolate(frame - showFrom, [0, 16], [0, 1], {
    extrapolateRight: 'clamp',
  });
  const ease = 1 - Math.pow(1 - p, 3);
  const dx = from === 'left' ? -distance : from === 'right' ? distance : 0;
  const dy = from === 'bottom' ? distance : from === 'top' ? -distance : 0;
  return (
    <div
      style={{
        opacity: ease,
        transform: `translate(${dx * (1 - ease)}px, ${dy * (1 - ease)}px)`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

// ---------- 用户消息气泡（右对齐+头像，拟真缺口补齐） ----------
export const UserBubble: React.FC<{ text: string; startFrame: number; cps?: number }> = ({
  text, startFrame, cps = 0.32,
}) => {
  const f = useCurrentFrame();
  if (f < startFrame) return null;
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 20, alignItems: 'flex-start' }}>
      <GlassPanel
        style={{
          maxWidth: '78%', borderRadius: '22px 22px 6px 22px',
          backgroundColor: 'rgba(48,54,61,0.9)', padding: '24px 30px',
        }}
      >
        <div style={{ fontFamily: F.body, fontSize: 40, color: C.text, lineHeight: 1.5 }}>
          <TypeText text={text} startFrame={startFrame} cps={cps} />
        </div>
      </GlassPanel>
      <div style={{
        width: 64, height: 64, borderRadius: '50%', flexShrink: 0,
        background: 'linear-gradient(135deg, #4a6fa5, #2c4a7c)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 34,
      }}>🧑</div>
    </div>
  );
};
