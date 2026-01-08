/**
 * Remotion Render Script v2.8.0
 * DailyInstagramの方式を参考に、Base64データURLを確実に処理
 *
 * 重要な変更点:
 * - Base64画像・音声データの詳細なログ
 * - propsの検証と正規化
 * - エラー時の詳細な診断情報
 */

import { bundle } from "@remotion/bundler";
import { renderMedia, selectComposition } from "@remotion/renderer";
import path from "path";
import fs from "fs";
import { fileURLToPath } from "url";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// CI環境かどうかを判定
const isCI = process.env.CI === 'true' || process.env.GITHUB_ACTIONS === 'true';

// GL mode selection
const getGlMode = () => {
  if (process.env.REMOTION_GL) {
    return process.env.REMOTION_GL;
  }
  return isCI ? 'swiftshader' : 'angle';
};

// Chromiumオプション
const chromiumOptions = {
  gl: getGlMode(),
  enableMultiProcessOnLinux: true,
  headless: true,
  ...(isCI && {
    disableWebSecurity: true,
    ignoreCertificateErrors: true,
  }),
};

/**
 * Base64データURLの検証
 */
function validateBase64DataUrl(dataUrl, type = 'unknown') {
  if (!dataUrl) {
    return { valid: false, reason: 'null or undefined' };
  }
  if (typeof dataUrl !== 'string') {
    return { valid: false, reason: `not a string: ${typeof dataUrl}` };
  }
  if (!dataUrl.startsWith('data:')) {
    return { valid: false, reason: 'does not start with data:' };
  }

  const match = dataUrl.match(/^data:([^;]+);base64,(.+)$/);
  if (!match) {
    return { valid: false, reason: 'invalid data URL format' };
  }

  const mimeType = match[1];
  const base64Data = match[2];
  const estimatedSize = Math.round(base64Data.length * 0.75);

  return {
    valid: true,
    mimeType,
    base64Length: base64Data.length,
    estimatedBytes: estimatedSize,
    preview: dataUrl.substring(0, 50) + '...'
  };
}

/**
 * propsを検証してログ出力
 */
function validateAndLogProps(inputProps) {
  console.log('\n[Remotion] ========== PROPS VALIDATION ==========');

  // 基本情報
  console.log(`[Remotion] title: ${inputProps.title || 'N/A'}`);
  console.log(`[Remotion] topic: ${inputProps.topic || 'N/A'}`);
  console.log(`[Remotion] slideDuration: ${inputProps.slideDuration || 5}s`);

  // スライドデータ
  const slides = inputProps.slides || [];
  console.log(`[Remotion] slides count: ${slides.length}`);
  slides.forEach((slide, i) => {
    console.log(`[Remotion]   slide[${i}]: type=${slide.type}, heading="${(slide.heading || '').substring(0, 30)}..."`);
  });

  // Base64画像
  const slideImages = inputProps.slideImages || [];
  console.log(`\n[Remotion] slideImages count: ${slideImages.length}`);
  slideImages.forEach((img, i) => {
    const validation = validateBase64DataUrl(img, `image[${i}]`);
    if (validation.valid) {
      console.log(`[Remotion]   image[${i}]: VALID (${validation.mimeType}, ~${Math.round(validation.estimatedBytes/1024)}KB)`);
    } else {
      console.log(`[Remotion]   image[${i}]: INVALID - ${validation.reason}`);
    }
  });

  // Base64音声
  console.log(`\n[Remotion] audioDataUrl: ${inputProps.audioDataUrl ? 'present' : 'absent'}`);
  if (inputProps.audioDataUrl) {
    const audioValidation = validateBase64DataUrl(inputProps.audioDataUrl, 'audio');
    if (audioValidation.valid) {
      console.log(`[Remotion]   audio: VALID (${audioValidation.mimeType}, ~${Math.round(audioValidation.estimatedBytes/1024)}KB)`);
    } else {
      console.log(`[Remotion]   audio: INVALID - ${audioValidation.reason}`);
    }
  }

  // フォールバック音声
  console.log(`[Remotion] audioUrl (fallback): ${inputProps.audioUrl || 'none'}`);
  if (inputProps.audioUrl) {
    const audioPath = path.join(__dirname, "public", inputProps.audioUrl);
    if (fs.existsSync(audioPath)) {
      const stats = fs.statSync(audioPath);
      console.log(`[Remotion]   file exists: ${stats.size} bytes`);
    } else {
      console.log(`[Remotion]   file NOT FOUND`);
    }
  }

  console.log('[Remotion] ========== END VALIDATION ==========\n');

  // 警告を出力
  if (slideImages.length === 0 && slides.length > 0) {
    console.warn('[Remotion] WARNING: No Base64 images provided! Video may show fallback images.');
  }

  if (slideImages.length > 0 && slideImages.length !== slides.length) {
    console.warn(`[Remotion] WARNING: Image count (${slideImages.length}) does not match slide count (${slides.length})`);
  }
}

async function render() {
  const args = process.argv.slice(2);
  const compositionId = args[0] || "SlideVideoV3";
  const outputPath = args[1] || path.join(__dirname, "out", "video.mp4");
  const propsFile = args[2];

  console.log(`[Remotion] ========================================`);
  console.log(`[Remotion] Remotion Render v2.8.0`);
  console.log(`[Remotion] ========================================`);
  console.log(`[Remotion] Composition: ${compositionId}`);
  console.log(`[Remotion] Output: ${outputPath}`);
  console.log(`[Remotion] Props file: ${propsFile || 'none'}`);
  console.log(`[Remotion] CI Environment: ${isCI}`);
  console.log(`[Remotion] GL mode: ${chromiumOptions.gl}`);

  // propsを読み込む
  let inputProps = {};
  if (propsFile && fs.existsSync(propsFile)) {
    try {
      const propsContent = fs.readFileSync(propsFile, "utf-8");
      console.log(`[Remotion] Props file size: ${propsContent.length} chars`);

      inputProps = JSON.parse(propsContent);
      console.log(`[Remotion] Props parsed successfully`);

      // 詳細な検証
      validateAndLogProps(inputProps);

    } catch (parseError) {
      console.error(`[Remotion] ERROR parsing props file: ${parseError.message}`);
      console.error(`[Remotion] This might be due to invalid JSON or encoding issues`);
      process.exit(1);
    }
  } else {
    console.log(`[Remotion] No props file provided, using defaults`);
  }

  // 出力ディレクトリを作成
  const outputDir = path.dirname(outputPath);
  if (!fs.existsSync(outputDir)) {
    fs.mkdirSync(outputDir, { recursive: true });
  }

  // GL modes to try
  const glModesToTry = isCI ? ['swiftshader', 'swangle', 'angle'] : ['angle'];
  let lastError = null;
  let bundled = null;

  // Webpackでバンドル
  console.log("\n[Remotion] Bundling...");
  try {
    bundled = await bundle({
      entryPoint: path.join(__dirname, "src", "index.tsx"),
      webpackOverride: (config) => config,
    });
    console.log("[Remotion] Bundle complete");
  } catch (bundleError) {
    console.error(`[Remotion] Bundle failed: ${bundleError.message}`);
    process.exit(1);
  }

  // 各GL modeを試行
  for (const glMode of glModesToTry) {
    console.log(`\n[Remotion] ========================================`);
    console.log(`[Remotion] Attempting render with GL mode: ${glMode}`);
    console.log(`[Remotion] ========================================`);

    const currentChromiumOptions = {
      ...chromiumOptions,
      gl: glMode,
    };

    try {
      // コンポジションを選択
      console.log("[Remotion] Selecting composition...");
      const composition = await selectComposition({
        serveUrl: bundled,
        id: compositionId,
        inputProps,
        chromiumOptions: currentChromiumOptions,
      });

      console.log(`[Remotion] Composition selected: ${composition.id}`);
      console.log(`[Remotion] Duration: ${composition.durationInFrames} frames @ ${composition.fps}fps`);
      console.log(`[Remotion] Size: ${composition.width}x${composition.height}`);

      // レンダリング実行
      console.log("[Remotion] Starting render...");
      const startTime = Date.now();

      await renderMedia({
        composition,
        serveUrl: bundled,
        codec: "h264",
        outputLocation: outputPath,
        inputProps,
        chromiumOptions: currentChromiumOptions,
        crf: 23,
        pixelFormat: "yuv420p",
        onProgress: ({ progress }) => {
          const percent = Math.round(progress * 100);
          if (percent % 10 === 0) {
            const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
            console.log(`[Remotion] Progress: ${percent}% (${elapsed}s elapsed)`);
          }
        },
      });

      const totalTime = ((Date.now() - startTime) / 1000).toFixed(1);
      console.log(`[Remotion] Render complete in ${totalTime}s`);

      // ファイルサイズを確認
      const stats = fs.statSync(outputPath);
      const sizeMB = (stats.size / 1024 / 1024).toFixed(2);
      console.log(`[Remotion] Output: ${outputPath}`);
      console.log(`[Remotion] File size: ${sizeMB} MB (${stats.size} bytes)`);

      if (stats.size < 10000) {
        console.error(`[Remotion] ERROR: File size too small (${stats.size} bytes)`);
        lastError = new Error(`File size too small: ${stats.size} bytes`);
        continue;
      }

      console.log(`[Remotion] SUCCESS with GL mode: ${glMode}`);
      process.exit(0);
    } catch (error) {
      console.error(`[Remotion] GL mode '${glMode}' failed: ${error.message}`);
      lastError = error;

      const modeIndex = glModesToTry.indexOf(glMode);
      if (modeIndex < glModesToTry.length - 1) {
        console.log(`[Remotion] Trying next GL mode...`);
        continue;
      }
    }
  }

  // 全て失敗
  const error = lastError || new Error("All GL modes failed");
  console.error(`[Remotion] FATAL ERROR: ${error.message}`);
  if (error.stack) {
    console.error(`[Remotion] Stack trace:\n${error.stack}`);
  }
  process.exit(1);
}

render();
