import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { F } from './Rich';

// 逐句字幕：按 subtitles.json 时间轴显示（旁白级跟句，非全程同显）
// 16:9 横屏布局：字幕带收窄到底部 60~150px（无竖屏平台 UI 预留）
import subsJson from '../subtitles.json';

export const Subtitles: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / 30; // fps=30
  const current = (subsJson as { start: number; end: number; text: string }[]).find(
    (s) => t >= s.start && t < s.end,
  );
  if (!current) return null;

  // 进出场淡入淡出
  const fadeIn = interpolate(t, [current.start, current.start + 0.15], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const fadeOut = interpolate(t, [current.end - 0.15, current.end], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const opacity = Math.min(fadeIn, fadeOut);

  // 单行自适应字号（永不折行），横屏可用宽度 1680
  const len = current.text.length;
  const fontSize = Math.max(24, Math.min(46, 1660 / len));

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 60,
        left: 120,
        right: 120,
        display: 'flex',
        justifyContent: 'center',
        opacity,
        pointerEvents: 'none',
      }}
    >
      <div
        style={{
          fontFamily: F.body,
          fontSize,
          fontWeight: 700,
          color: '#ffffff',
          lineHeight: 1.35,
          textAlign: 'center',
          whiteSpace: 'nowrap',
          backgroundColor: 'rgba(8,10,14,0.82)',
          borderRadius: 14,
          padding: '12px 30px',
          border: '1px solid rgba(240,246,252,0.12)',
          maxWidth: '100%',
        }}
      >
        {current.text}
      </div>
    </div>
  );
};
