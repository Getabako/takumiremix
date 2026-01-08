import React, { useMemo } from "react";
import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  Audio,
  Img,
  Sequence
} from "remotion";

/**
 * SlideVideoV3 - Marp Slides to Video
 *
 * Marp CLIで生成されたスライドPNG画像を動画化
 * - スライド画像をフルスクリーン表示
 * - 音声同期
 * - 字幕表示
 * - Ken Burnsエフェクト
 */

// 型定義
interface Subtitle {
  text: string;
  startFrame: number;
  endFrame: number;
}

interface SlideData {
  type: "title" | "content" | "ending";
  heading: string;
  subheading?: string;
  points?: string[];
  startFrame: number;
  endFrame: number;
  duration: number;
  audioBase64?: string | null;
  subtitles?: Subtitle[];
}

export interface SlideVideoV3Props {
  title: string;
  topic: string;
  fps: number;
  totalFrames: number;
  slides: SlideData[];
  slideImages: string[];  // Base64エンコードされた画像
}

// トピック別カラースキーム
const TOPIC_COLORS: Record<string, { primary: string; secondary: string; bg: string }> = {
  psychology: { primary: "#00b4d8", secondary: "#90e0ef", bg: "#1a1a2e" },
  education: { primary: "#10b981", secondary: "#6ee7b7", bg: "#1a1a2e" },
  startup: { primary: "#f59e0b", secondary: "#fcd34d", bg: "#1a1a2e" },
  investment: { primary: "#14b8a6", secondary: "#5eead4", bg: "#1a1a2e" },
  ai_tools: { primary: "#3b82f6", secondary: "#93c5fd", bg: "#1a1a2e" },
  inclusive_education: { primary: "#06b6d4", secondary: "#67e8f9", bg: "#1a1a2e" },
  weekly_summary: { primary: "#0ea5e9", secondary: "#7dd3fc", bg: "#1a1a2e" }
};

// 現在のスライドを見つける
function findCurrentSlide(slides: SlideData[], frame: number): { slide: SlideData | null; index: number } {
  const index = slides.findIndex(
    slide => frame >= slide.startFrame && frame < slide.endFrame
  );
  return {
    slide: index >= 0 ? slides[index] : null,
    index: index >= 0 ? index : slides.length - 1
  };
}

// 現在の字幕を見つける
function findCurrentSubtitle(subtitles: Subtitle[] | undefined, frame: number): Subtitle | null {
  if (!subtitles) return null;
  return subtitles.find(
    sub => frame >= sub.startFrame && frame < sub.endFrame
  ) || null;
}

// スライドシーンコンポーネント
const SlideScene: React.FC<{
  slide: SlideData;
  slideIndex: number;
  totalSlides: number;
  colors: { primary: string; secondary: string; bg: string };
  slideImage: string;
  globalFrame: number;
}> = ({ slide, slideIndex, totalSlides, colors, slideImage, globalFrame }) => {
  const { fps } = useVideoConfig();

  // スライド内のローカルフレーム
  const localFrame = globalFrame - slide.startFrame;
  const slideDuration = slide.endFrame - slide.startFrame;

  // トランジション（15フレーム = 0.5秒）
  const transitionFrames = Math.min(15, slideDuration / 4);

  // フェードイン
  const fadeIn = interpolate(
    localFrame,
    [0, transitionFrames],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  // フェードアウト（最後のスライドは完全にフェードしない）
  const isLast = slideIndex === totalSlides - 1;
  const fadeOut = isLast ? 1 : interpolate(
    localFrame,
    [slideDuration - transitionFrames, slideDuration],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const opacity = Math.min(fadeIn, fadeOut);

  // Ken Burnsエフェクト（ゆっくりズーム）
  const kenBurnsScale = interpolate(
    localFrame,
    [0, slideDuration],
    [1.02, 1.0],
    { extrapolateRight: "clamp" }
  );

  // 微小なパン効果
  const kenBurnsX = interpolate(
    localFrame,
    [0, slideDuration],
    [slideIndex % 2 === 0 ? -5 : 5, 0],
    { extrapolateRight: "clamp" }
  );

  // 現在の字幕
  const currentSubtitle = findCurrentSubtitle(slide.subtitles, globalFrame);

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg, opacity }}>
      {/* スライド画像（Marp生成のPNG） */}
      {slideImage && (
        <AbsoluteFill
          style={{
            transform: `scale(${kenBurnsScale}) translateX(${kenBurnsX}px)`,
          }}
        >
          <Img
            src={slideImage}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",  // スライドを収まるように表示
            }}
          />
        </AbsoluteFill>
      )}

      {/* 字幕 */}
      {currentSubtitle && (
        <div
          style={{
            position: "absolute",
            bottom: 60,
            left: "10%",
            right: "10%",
            textAlign: "center",
            fontSize: 32,
            color: "white",
            fontFamily: "'Noto Sans JP', 'M PLUS 2', sans-serif",
            fontWeight: 600,
            textShadow: "2px 2px 8px rgba(0,0,0,0.9), 0 0 20px rgba(0,0,0,0.7)",
            lineHeight: 1.5,
            backgroundColor: "rgba(0,0,0,0.6)",
            padding: "16px 32px",
            borderRadius: 12,
            opacity: interpolate(
              globalFrame,
              [currentSubtitle.startFrame, currentSubtitle.startFrame + 5, currentSubtitle.endFrame - 5, currentSubtitle.endFrame],
              [0, 1, 1, 0],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            )
          }}
        >
          {currentSubtitle.text}
        </div>
      )}

      {/* プログレスバー */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          width: `${(localFrame / slideDuration) * 100}%`,
          height: 4,
          backgroundColor: colors.primary,
          transition: "width 0.1s linear"
        }}
      />

      {/* スライド番号 */}
      <div
        style={{
          position: "absolute",
          bottom: 16,
          right: 24,
          fontSize: 20,
          color: "rgba(255,255,255,0.6)",
          fontFamily: "sans-serif",
        }}
      >
        {slideIndex + 1} / {totalSlides}
      </div>
    </AbsoluteFill>
  );
};

// メインコンポーネント
export const SlideVideoV3: React.FC<SlideVideoV3Props> = ({
  title,
  topic,
  fps,
  totalFrames,
  slides,
  slideImages
}) => {
  const frame = useCurrentFrame();
  const colors = TOPIC_COLORS[topic] || TOPIC_COLORS.ai_tools;

  // デバッグログ（初回のみ）
  if (frame === 0) {
    console.log('[SlideVideoV3] Rendering:', {
      title,
      topic,
      fps,
      totalFrames,
      slidesCount: slides?.length,
      imagesCount: slideImages?.length
    });
  }

  // 現在のスライドを見つける
  const { slide: currentSlide, index: currentSlideIndex } = useMemo(() => {
    return findCurrentSlide(slides || [], frame);
  }, [slides, frame]);

  // スライドがない場合
  if (!slides || slides.length === 0) {
    console.error('[SlideVideoV3] No slides provided');
    return (
      <AbsoluteFill style={{ backgroundColor: colors.bg }}>
        <div style={{
          color: 'white',
          textAlign: 'center',
          marginTop: 200,
          fontSize: 48,
          fontFamily: 'sans-serif'
        }}>
          Loading...
        </div>
      </AbsoluteFill>
    );
  }

  // 現在のスライドがない場合（フレーム範囲外）は最後のスライドを表示
  const displaySlide = currentSlide || slides[slides.length - 1];
  const displayIndex = currentSlide ? currentSlideIndex : slides.length - 1;

  // 背景画像
  const slideImage = slideImages && slideImages[displayIndex]
    ? slideImages[displayIndex]
    : "";

  return (
    <AbsoluteFill style={{ backgroundColor: colors.bg }}>
      {/* 現在のスライドシーン */}
      <SlideScene
        slide={displaySlide}
        slideIndex={displayIndex}
        totalSlides={slides.length}
        colors={colors}
        slideImage={slideImage}
        globalFrame={frame}
      />

      {/* スライドごとの音声 */}
      {slides.map((slide, index) => {
        if (!slide.audioBase64) return null;

        return (
          <Sequence
            key={`audio-${index}`}
            from={slide.startFrame}
            durationInFrames={slide.endFrame - slide.startFrame}
          >
            <Audio
              src={slide.audioBase64}
              volume={1}
            />
          </Sequence>
        );
      })}
    </AbsoluteFill>
  );
};

export default SlideVideoV3;
