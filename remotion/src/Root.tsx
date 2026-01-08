import { Composition } from "remotion";
import { BlogVideo, BlogVideoProps } from "./compositions/BlogVideo";
import { SlideVideo, SlideVideoProps } from "./compositions/SlideVideo";
import { SlideVideoV3, SlideVideoV3Props } from "./compositions/SlideVideoV3";

// デフォルトのブログデータ（プレビュー用）
const defaultBlogData: BlogVideoProps = {
  title: "AIツールの最新動向2025",
  summary: "2025年のAIツールトレンドを詳しく解説します。",
  points: [
    "生成AIの進化と実用化",
    "業務効率化ツールの普及",
    "セキュリティとプライバシーの重要性"
  ],
  topic: "ai_tools",
  date: "2025年12月30日",
  authorName: "if(塾) Blog"
};

// スライド動画のデフォルトデータ（プレビュー用）
const defaultSlideData: SlideVideoProps = {
  title: "AIツールの最新動向2025",
  slides: [
    {
      type: "title",
      heading: "AIツールの最新動向2025",
      subheading: "生成AIがもたらす変革"
    },
    {
      type: "content",
      heading: "生成AIの進化",
      points: [
        "テキスト生成の高度化",
        "画像・動画生成の実用化",
        "マルチモーダルAIの普及"
      ]
    },
    {
      type: "content",
      heading: "業務効率化ツール",
      points: [
        "コード生成支援",
        "文書作成の自動化",
        "データ分析の簡易化"
      ]
    },
    {
      type: "ending",
      heading: "if(塾) Blog",
      subheading: "詳しくはブログで"
    }
  ],
  topic: "ai_tools",
  authorName: "if(塾) Blog",
  slideDuration: 5
};

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* メインのブログ動画 - 30秒版 */}
      <Composition
        id="BlogVideo"
        component={BlogVideo}
        durationInFrames={900}  // 30秒 @ 30fps
        fps={30}
        width={1920}
        height={1080}
        defaultProps={defaultBlogData}
      />

      {/* ショート動画 - 15秒版 */}
      <Composition
        id="BlogVideoShort"
        component={BlogVideo}
        durationInFrames={450}  // 15秒 @ 30fps
        fps={30}
        width={1080}
        height={1920}  // 縦型（Shorts/Reels用）
        defaultProps={{
          ...defaultBlogData,
          isShort: true
        }}
      />

      {/* スライドベース動画（可変長） */}
      <Composition
        id="SlideVideo"
        component={SlideVideo}
        durationInFrames={1800}  // 60秒 @ 30fps（デフォルト、propsで調整）
        fps={30}
        width={1920}
        height={1080}
        defaultProps={defaultSlideData}
        calculateMetadata={({ props }) => {
          // スライド数と表示時間から動画長を計算
          const slideCount = props.slides?.length || 4;
          const slideDuration = props.slideDuration || 5;
          const fps = 30;
          return {
            durationInFrames: slideCount * slideDuration * fps
          };
        }}
      />

      {/* スライドベースショート動画 */}
      <Composition
        id="SlideVideoShort"
        component={SlideVideo}
        durationInFrames={900}  // 30秒 @ 30fps
        fps={30}
        width={1080}
        height={1920}  // 縦型
        defaultProps={{
          ...defaultSlideData,
          slideDuration: 3  // ショート版は各スライド3秒
        }}
      />

      {/* SlideVideoV3 - タイミングベース動画（SlideMovie_WorkFlow方式） */}
      <Composition
        id="SlideVideoV3"
        component={SlideVideoV3}
        durationInFrames={1800}  // デフォルト60秒、propsで上書き
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          title: "タイトル",
          topic: "ai_tools",
          fps: 30,
          totalFrames: 1800,
          slides: [],
          slideImages: []
        }}
        calculateMetadata={({ props }) => {
          // totalFramesからdurationInFramesを計算
          const totalFrames = props.totalFrames || 1800;
          return {
            durationInFrames: totalFrames,
            fps: props.fps || 30
          };
        }}
      />
    </>
  );
};
