import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { F } from './Rich';

// 逐句字幕：按 subtitles.json 时间轴显示（旁白级跟句，非全程同显）
import subsJson from '../subtitles.json';

export const Subtitles: React.FC = () => {
  const frame = useCurrentFrame();
  const t = frame / 30; // fps=30
  const current = subsJson.find((s) => t >= s.start && t < s.end);
  if (!current) return null;

  // 进出场淡入淡出
  const fadeIn = interpolate(t, [current.start, current.start + 0.15], [0, 1], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const fadeOut = interpolate(t, [current.end - 0.15, current.end], [1, 0], {
    extrapolateLeft: 'clamp', extrapolateRight: 'clamp',
  });
  const opacity = Math.min(fadeIn, fadeOut);

  // 长句缩字号
  const len = current.text.length;
  const fontSize = len > 22 ? 46 : len > 14 ? 52 : 58;

  return (
    <div
      style={{
        position: 'absolute',
        bottom: 88,
        left: 50,
        right: 50,
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
          backgroundColor: 'rgba(8,10,14,0.82)',
          borderRadius: 16,
          padding: '16px 34px',
          border: '1px solid rgba(240,246,252,0.12)',
          maxWidth: '100%',
        }}
      >
        {current.text}
      </div>
    </div>
  );
};
