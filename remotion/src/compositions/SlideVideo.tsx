import React from "react";
import {
  AbsoluteFill,
  Sequence,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
  Audio,
  Img,
  Easing
} from "remotion";

// トピック別カラースキーム（紫禁止）
const TOPIC_COLORS: Record<string, { primary: string; secondary: string; bg: string }> = {
  psychology: { primary: "#00b4d8", secondary: "#90e0ef", bg: "#1a1a2e" },
  education: { primary: "#10b981", secondary: "#6ee7b7", bg: "#1a1a2e" },
  startup: { primary: "#f59e0b", secondary: "#fcd34d", bg: "#1a1a2e" },
  investment: { primary: "#14b8a6", secondary: "#5eead4", bg: "#1a1a2e" },
  ai_tools: { primary: "#3b82f6", secondary: "#93c5fd", bg: "#1a1a2e" },
  inclusive_education: { primary: "#06b6d4", secondary: "#67e8f9", bg: "#1a1a2e" },
  weekly_summary: { primary: "#0ea5e9", secondary: "#7dd3fc", bg: "#1a1a2e" }
};

export interface SlideVideoProps {
  title: string;
  slides: SlideData[];
  topic: string;
  authorName?: string;
  audioUrl?: string | null;
  audioDataUrl?: string | null;
  slideImagePrefix?: string;
  slideDuration?: number;
  slideImages?: string[];
}

interface SlideData {
  heading: string;
  subheading?: string;
  points?: string[];
  type: "title" | "content" | "ending";
  imageUrl?: string;
  narrationText?: string;
}

// スライドシーン（DailyInstagram方式を参考にシンプル化）
const SlideScene: React.FC<{
  slide: SlideData;
  slideNumber: number;
  totalSlides: number;
  colors: { primary: string; secondary: string; bg: string };
  backgroundImage?: string;
  isFirst: boolean;
  isLast: boolean;
}> = ({ slide, slideNumber, totalSlides, colors, backgroundImage, isFirst, isLast }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();

  const transitionDuration = 15; // 0.5秒のトランジション

  // フェードイン（最初の0.5秒）
  const fadeIn = interpolate(
    frame,
    [0, transitionDuration],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // フェードアウト（最後のスライド以外、最後の0.5秒）
  const fadeOut = isLast ? 1 : interpolate(
    frame,
    [durationInFrames - transitionDuration, durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const opacity = Math.min(fadeIn, fadeOut);

  // Ken Burns エフェクト（背景画像用）
  const kenBurnsScale = interpolate(
    frame,
    [0, durationInFrames],
    [1.05, 1.0],
    { extrapolateRight: "clamp" }
  );

  const kenBurnsX = interpolate(
    frame,
    [0, durationInFrames],
    [slideNumber % 2 === 0 ? -15 : 15, 0],
    { extrapolateRight: "clamp" }
  );

  // テキストアニメーション
  const textSpring = spring({
    frame: frame - 10,
    fps,
    config: { damping: 100, stiffness: 200, mass: 0.5 }
  });

  const headingY = interpolate(textSpring, [0, 1], [40, 0]);
  const headingOpacity = interpolate(textSpring, [0, 1], [0, 1]);

  const pointsDelay = 20;

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, opacity }}>
      {/* 背景画像（Ken Burns エフェクト） */}
      {backgroundImage && (
        <AbsoluteFill
          style={{
            transform: `scale(${kenBurnsScale}) translateX(${kenBurnsX}px)`,
          }}
        >
          <Img
            src={backgroundImage}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              opacity: 0.6
            }}
          />
          {/* グラデーションオーバーレイ */}
          <AbsoluteFill
            style={{
              background: `linear-gradient(to bottom, ${colors.bg}dd 0%, ${colors.bg}88 40%, ${colors.bg}dd 100%)`
            }}
          />
        </AbsoluteFill>
      )}

      {/* コンテンツ */}
      <AbsoluteFill
        style={{
          padding: slide.type === "title" ? 100 : 80,
          justifyContent: slide.type === "title" ? "center" : "flex-start",
          alignItems: slide.type === "title" ? "center" : "flex-start",
          display: "flex",
          flexDirection: "column"
        }}
      >
        {/* スライド番号（title/ending以外） */}
        {slide.type === "content" && (
          <div
            style={{
              position: "absolute",
              top: 40,
              right: 60,
              fontSize: 24,
              color: colors.secondary,
              opacity: headingOpacity,
              fontFamily: "sans-serif"
            }}
          >
            {slideNumber} / {totalSlides}
          </div>
        )}

        {/* 見出し */}
        <h1
          style={{
            fontSize: slide.type === "title" ? 72 : 56,
            fontWeight: 800,
            color: colors.primary,
            textAlign: slide.type === "title" ? "center" : "left",
            marginBottom: 24,
            opacity: headingOpacity,
            transform: `translateY(${headingY}px)`,
            textShadow: "0 4px 20px rgba(0,0,0,0.5)",
            maxWidth: "90%",
            fontFamily: "sans-serif",
            lineHeight: 1.3
          }}
        >
          {slide.heading}
        </h1>

        {/* サブ見出し */}
        {slide.subheading && (
          <h2
            style={{
              fontSize: slide.type === "title" ? 40 : 32,
              fontWeight: 600,
              color: colors.secondary,
              textAlign: slide.type === "title" ? "center" : "left",
              marginBottom: 40,
              opacity: interpolate(frame, [15, 30], [0, 1], { extrapolateRight: "clamp" }),
              fontFamily: "sans-serif"
            }}
          >
            {slide.subheading}
          </h2>
        )}

        {/* ポイント（箇条書き） */}
        {slide.points && slide.points.length > 0 && (
          <ul
            style={{
              listStyle: "none",
              padding: 0,
              marginTop: 40
            }}
          >
            {slide.points.map((point, index) => {
              const pointFrame = frame - pointsDelay - index * 10;
              const pointSpring = spring({
                frame: pointFrame,
                fps,
                config: { damping: 100, stiffness: 200, mass: 0.5 }
              });
              const pointOpacity = interpolate(pointSpring, [0, 1], [0, 1]);
              const pointX = interpolate(pointSpring, [0, 1], [60, 0]);

              return (
                <li
                  key={index}
                  style={{
                    fontSize: 32,
                    color: "white",
                    marginBottom: 24,
                    opacity: pointOpacity,
                    transform: `translateX(${pointX}px)`,
                    display: "flex",
                    alignItems: "flex-start",
                    fontFamily: "sans-serif",
                    lineHeight: 1.4
                  }}
                >
                  <span
                    style={{
                      display: "inline-block",
                      width: 14,
                      height: 14,
                      backgroundColor: colors.primary,
                      borderRadius: "50%",
                      marginRight: 20,
                      marginTop: 10,
                      flexShrink: 0
                    }}
                  />
                  {point}
                </li>
              );
            })}
          </ul>
        )}

        {/* エンディング時のCTA */}
        {slide.type === "ending" && (
          <div
            style={{
              position: "absolute",
              bottom: 120,
              left: 0,
              right: 0,
              textAlign: "center",
              opacity: interpolate(frame, [30, 50], [0, 1], { extrapolateRight: "clamp" })
            }}
          >
            <p style={{ fontSize: 28, color: "rgba(255,255,255,0.8)", fontFamily: "sans-serif" }}>
              ブログで詳しく読む
            </p>
          </div>
        )}
      </AbsoluteFill>

      {/* 下部プログレスバー */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: `${(frame / durationInFrames) * 100}%`,
          height: 6,
          backgroundColor: colors.primary
        }}
      />
    </AbsoluteFill>
  );
};

// メインのSlideVideoコンポーネント
export const SlideVideo: React.FC<SlideVideoProps> = ({
  title,
  slides,
  topic,
  authorName = "if(塾) Blog",
  audioUrl = null,
  audioDataUrl = null,
  slideImagePrefix = "slide_",
  slideDuration = 5,
  slideImages = []
}) => {
  const { fps, durationInFrames } = useVideoConfig();
  const colors = TOPIC_COLORS[topic] || TOPIC_COLORS.ai_tools;

  // 各スライドの長さ（フレーム単位）
  const slideFrames = slideDuration * fps;

  // デバッグログ（開発時のみ有効化）
  console.log('[SlideVideo] Rendering with props:', {
    title,
    topic,
    slideDuration,
    slidesCount: slides?.length,
    slideImagesCount: slideImages?.length,
    hasAudioDataUrl: !!audioDataUrl,
    hasAudioUrl: !!audioUrl,
    totalDuration: durationInFrames,
    slideFrames
  });

  // オーディオトラック（Base64データURL優先）
  // DailyInstagramと同様、Base64データURLを直接使用
  let audioElement: JSX.Element | null = null;

  if (audioDataUrl && audioDataUrl.startsWith('data:')) {
    console.log('[SlideVideo] Using Base64 audio data URL');
    audioElement = <Audio key="audio" src={audioDataUrl} volume={1} />;
  } else if (audioUrl && audioUrl.startsWith('data:')) {
    console.log('[SlideVideo] Using audioUrl as Base64');
    audioElement = <Audio key="audio" src={audioUrl} volume={1} />;
  }

  // スライドシーケンスを構築
  const slideSequences: JSX.Element[] = [];
  let currentFrame = 0;

  if (!slides || slides.length === 0) {
    console.error('[SlideVideo] No slides provided!');
    return (
      <AbsoluteFill style={{ backgroundColor: colors.bg }}>
        <div style={{ color: 'white', textAlign: 'center', marginTop: 200 }}>
          No slides to display
        </div>
      </AbsoluteFill>
    );
  }

  slides.forEach((slide, index) => {
    // 背景画像を取得（Base64優先）
    let backgroundImage: string | undefined = undefined;

    // 1. slideImages配列から取得（Base64データURL）
    if (slideImages && slideImages.length > index && slideImages[index]) {
      const imgData = slideImages[index];
      if (imgData && typeof imgData === 'string' && imgData.startsWith('data:')) {
        backgroundImage = imgData;
        console.log(`[SlideVideo] Slide ${index}: using Base64 image`);
      }
    }

    // 2. slide.imageUrlから取得（Base64またはデータURL）
    if (!backgroundImage && slide.imageUrl) {
      if (slide.imageUrl.startsWith('data:')) {
        backgroundImage = slide.imageUrl;
        console.log(`[SlideVideo] Slide ${index}: using slide.imageUrl (Base64)`);
      }
    }

    slideSequences.push(
      <Sequence
        key={`slide-${index}`}
        from={currentFrame}
        durationInFrames={slideFrames}
      >
        <SlideScene
          slide={slide}
          slideNumber={index + 1}
          totalSlides={slides.length}
          colors={colors}
          backgroundImage={backgroundImage}
          isFirst={index === 0}
          isLast={index === slides.length - 1}
        />
      </Sequence>
    );

    currentFrame += slideFrames;
  });

  console.log(`[SlideVideo] Created ${slideSequences.length} slide sequences, total frames: ${currentFrame}`);

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      {/* オーディオ（最初に配置してビデオ全体で再生） */}
      {audioElement}

      {/* スライドシーケンス */}
      {slideSequences}
    </AbsoluteFill>
  );
};

export default SlideVideo;
