import { Config } from "@remotion/cli/config";

/**
 * Remotion Configuration
 * ブログ動画・スライド動画生成用の設定
 */

// 出力設定
Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

// 品質設定
Config.setJpegQuality(90);

// パフォーマンス設定
Config.setConcurrency(4);

// ログ設定
Config.setLevel("verbose");
