import React from 'react';
import { useCurrentFrame, interpolate } from 'remotion';
import { C } from '../theme';

// 底部知识点字幕浮层：黄绿高亮描边，观众截图用的那张卡
export const Caption: React.FC<{ text: string; showFrom: number }> = ({
  text,
  showFrom,
}) => {
  const frame = useCurrentFrame();
  if (frame < showFrom) return null;
  const opacity = interpolate(frame, [showFrom, showFrom + 8], [0, 1], {
    extrapolateRight: 'clamp',
  });
  const slide = interpolate(frame, [showFrom, showFrom + 10], [30, 0], {
    extrapolateRight: 'clamp',
  });
  return (
    <div
      style={{
        position: 'absolute',
        bottom: 150,
        left: 60,
        right: 60,
        display: 'flex',
        justifyContent: 'center',
        opacity,
        transform: `translateY(${slide}px)`,
      }}
    >
      <div
        style={{
          backgroundColor: 'rgba(13,17,23,0.86)',
          border: `3px solid ${C.accent}`,
          borderRadius: 20,
          padding: '22px 40px',
          fontSize: 46,
          fontWeight: 800,
          color: C.accent,
          boxShadow: `0 0 34px ${C.accent}44`,
          textAlign: 'center',
        }}
      >
        {text}
      </div>
    </div>
  );
};

// 右下角常驻署名角标（P2 起全片显示，防侵权）
export const Badge: React.FC = () => (
  <div
    style={{
      position: 'absolute',
      right: 28,
      top: 60,
      fontSize: 24,
      color: C.muted,
      backgroundColor: 'rgba(13,17,23,0.7)',
      padding: '10px 20px',
      borderRadius: 12,
      border: `1px solid ${C.border}`,
    }}
  >
    方法出处：MIT研究生@X ｜ 中文：抖音 @学习有了方法
  </div>
);
