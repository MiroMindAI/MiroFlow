<div align="center">
  <img src="docs/mkdocs/docs/assets/miroflow_logo.png" width="100%" alt="MiroFlow" />
</div>

<br> 

<div align="center">

[![ドキュメント](https://img.shields.io/badge/Documentation-4285F4?style=for-the-badge&logo=gitbook&logoColor=white)](https://miromindai.github.io/MiroFlow/)
[![デモ](https://img.shields.io/badge/Demo-FFB300?style=for-the-badge&logo=airplayvideo&logoColor=white)](https://dr.miromind.ai/)
[![モデル](https://img.shields.io/badge/Models-5EDDD2?style=for-the-badge&logo=huggingface&logoColor=ffffff&labelColor)](https://huggingface.co/collections/miromind-ai/mirothinker-v02-68af084a18035f57b17cd902)
[![データ](https://img.shields.io/badge/Data-0040A1?style=for-the-badge&logo=huggingface&logoColor=ffffff&labelColor)](https://huggingface.co/datasets/miromind-ai/MiroVerse-v0.1)

[![GITHUB](https://img.shields.io/badge/Github-24292F?style=for-the-badge&logo=github&logoColor=white)](https://github.com/MiroMindAI)
[![ウェブサイト](https://img.shields.io/badge/Website-4285F4?style=for-the-badge&logo=google-chrome&logoColor=white)](https://miromind.ai/)
[![DISCORD](https://img.shields.io/badge/Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com/invite/GPqEnkzQZd)
[![WeChat](https://img.shields.io/badge/WeChat-07C160?style=for-the-badge&logo=wechat&logoColor=white)](https://huggingface.co/datasets/miromind-ai/MiroFlow-Benchmarks/resolve/main/assets/wechat.png)
[![RedNote](https://img.shields.io/badge/RedNote-FF2442?style=for-the-badge&logo=revoltdotchat&logoColor=white)](https://www.xiaohongshu.com/user/profile/5e353bd80000000001000239)

</div>

<div align="center">

### 🚀 [Try our Demo!](https://dr.miromind.ai/) | 📚 [Full Documentation](https://miromindai.github.io/MiroFlow/)｜[English](README.md)｜[中文](README_zh.md)

</div>

<table align="center" style="border: 1px solid #ccc; border-radius: 8px; padding: 12px; background-color: #f9f9f9; width: 60%;">
  <tr>
    <td style="text-align: center; padding: 10px;">
      <strong>研究アシスタントデモ</strong> - 
      <span style="font-size: 0.9em; color: #555;">CVPR 2025最優秀論文を読み、研究アドバイスを提供</span>
      <br>
      <video src="https://github.com/user-attachments/assets/99ed3172-6e9a-467a-9ccb-be45957fe2e4"
             controls muted preload="metadata"
             width="50%" height="50%"
      </video>
    </td>
  </tr>
</table>

## 📋 目次

- [📰 ニュース・アップデート](#-ニュースアップデート)
- [🤖 MiroFlowとは？](#-miroflowとは)
- [✨ ベンチマーク性能](#-ベンチマーク性能)
- [🚀 5分で始める](#-5分で始める)
- [🤖 MiroFlowフレームワーク](#-miroflow-aiエージェント基盤フレームワーク)
- [🤝 貢献](#-貢献)
- [❓ よくある質問](#-よくある質問)
- [📄 ライセンス・サポート](#-ライセンスサポート)
- [👥 謝辞・貢献者](#-謝辞貢献者)

## 📰 ニュース・アップデート

- **[2025-09-15]**: 🎉🎉 **MiroFlow v0.3** - 強化されたコードベースアーキテクチャと大幅に改善されたベンチマーク性能。MiroFlowが未来予測ベンチマークで1位を獲得。
- **[2025-08-27]**: **MiroFlow v0.2** - [複数のエージェントベンチマーク](https://miromind.ai/blog/miroflow)で最先端の性能を達成、HLE (27.2%)、HLE-Text-Only (29.5%)、BrowserComp-EN (33.2%)、BrowserComp-ZH (47.1%)、xBench-DeepSearch (72.0%)を含む
- **[2025-08-26]**: [GAIA検証トレース](docs/public_trace.md) (73.94% pass@1) とローカルデプロイメント用の[Gradioデモ](https://github.com/MiroMindAI/MiroThinker/tree/main/apps/gradio-demo)をリリース
- **[2025-08-08]**: 🎉 **MiroFlow v0.1** - フレームワーク、モデル、トレーニングデータの完全なオープンソースリリース

---

## 🤖 MiroFlowとは？

**MiroFlow**は、複雑な推論タスクで最先端の性能を実現する知的AIエージェントを構築するための包括的なフレームワークです。強化された会話管理、柔軟なツール統合、複数のデータセットにわたる広範囲なベンチマーク評価を提供します。

**MiroThinker**は、このフレームワーク上に構築されたオープンソースエージェントモデルシリーズです。

### 🌟 主要ハイライト

- 🏆 **最先端の性能**: [複数のエージェントベンチマーク](https://miromindai.github.io/MiroFlow/evaluation_overview/)で1位ランキング
- 📊 **プレミアムトレーニングデータ**: [MiroVerse](https://huggingface.co/datasets/miromind-ai/MiroVerse-v0.1)による厳選されたデータセット
- 🤖 **オープンモデル**: [MiroThinker](https://huggingface.co/collections/miromind-ai/mirothinker-v01-689301b6d0563321862d44a1)での完全なコレクション
- 🔧 **完全なトレーニングスタック**: [MiroTrain](https://github.com/MiroMindAI/MiroTrain)でのSFT/DPOレシピ
- 🎯 **高度な強化学習**: [MiroRL](https://github.com/MiroMindAI/MiroRL)による強化学習

### ✨ ベンチマーク性能

<img width="100%" alt="image" src="docs/mkdocs/docs/assets/futurex-09-12.png" />

2025年9月10日時点で、FutureXベンチマークリーダーボードで1位を獲得しました。

<div align="center">
  <img src="docs/mkdocs/docs/assets/miroflow-0.2-performance_short.png" width="90%" alt="包括的なベンチマーク性能比較" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(3, 3, 3, 0.1);">
</div>

**GAIA**、**HLE**、**BrowseComp**、**xBench-DeepSearch**を含む一連のベンチマークでMiroFlowを評価し、最先端の結果を達成しました。

| モデル/フレームワーク | GAIA Val | HLE | HLE-Text | BrowserComp-EN | BrowserComp-ZH | xBench-DeepSearch |
|------------------|----------|-----|----------|----------------|----------------|-------------------|
| **MiroFlow** | **82.4%** | **27.2%** | 29.5% | 33.2% | **47.1%** | **72.0%** |
| OpenAI Deep Research | 67.4% | 26.6% | - | **51.5%** | 42.9% | - |
| Gemini Deep Research | - | 26.9% | - | - | - | 50+% |
| Kimi Researcher | - | - | 26.9% | - | - | 69.0% |
| WebSailor-72B | 55.4% | - | - | - | 30.1% | 55.0% |
| Manus | 73.3% | - | - | - | - | - |
| DeepSeek v3.1 | - | - | **29.8%** | - | - | 71.2% |

# 🚀 5分で始める

リポジトリをクローンし、APIキーを設定して、初めての知的AIエージェントを実行しましょう。必要なのは`OPENROUTER_API_KEY`だけです。

## 📋 前提条件

- **Python**: 3.12以上
- **パッケージマネージャー**: [`uv`](https://docs.astral.sh/uv/)
- **オペレーティングシステム**: Linux, macOS

## ⚡ クイックセットアップ

**例**: ファイル処理機能を持つ知的文書解析。

```bash
# 1. クローンとセットアップ
git clone https://github.com/MiroMindAI/MiroFlow && cd MiroFlow
uv sync

# 2. APIキーの設定
cp .env.template .env
# .envを編集してOPENROUTER_API_KEYを追加

# 3. 初めてのエージェントを実行
uv run main.py trace --config_file_name=agent_quickstart_1 --task="What is the first country listed in the XLSX file that have names starting with Co?" --task_file_name="data/FSI-2023-DOWNLOAD.xlsx"
```

🎉 **期待される出力**: エージェントは **\boxed{Congo Democratic Republic}** を返すはずです 😊

> **💡 ヒント**: 問題が発生した場合は、APIキーが`.env`ファイルで正しく設定されており、すべての依存関係がインストールされていることを確認してください。

**🎯 包括的なベンチマークスイート**:
- **GAIA Validation**: 汎用AIアシスタントのベンチマーク。([論文](https://arxiv.org/abs/2311.12983))
- **GAIA-Text-103**: テキストのみのタスクのためのGAIA Validationのサブセット。([論文](https://arxiv.org/abs/2505.22648))
- **HLE**: 人類最後の試験。([論文](https://arxiv.org/abs/2501.14249))
- **HLE-Text-500**: テキストのみのタスクのためのHLEのサブセット。([論文](https://arxiv.org/pdf/2504.21776))

詳細なガイドに従って、[ベンチマークドキュメント](https://miromindai.github.io/MiroFlow/evaluation_overview/)でベンチマーク結果を再現してください

# 🤖 MiroFlow: AIエージェント基盤フレームワーク

MiroFlowは、複雑な推論タスクで最先端の結果を提供する知的AIエージェントを構築するための高性能でモジュラーなフレームワークです。このフレームワークは、高度なマルチターン会話機能、広範囲なツールエコシステム統合、最適なタスク完了のための階層的サブエージェントオーケストレーションを特徴としています。エージェントの[ワークフローアーキテクチャ](https://miromindai.github.io/MiroFlow/core_concepts/)についてもっと学んでください。

<div align="center">
<img src="docs/mkdocs/docs/assets/miroflow_architecture.png" width="100%" alt="MiroFlowアーキテクチャ">
</div>

## 🤝 貢献

コミュニティからの貢献を歓迎します！バグの修正、機能の追加、ドキュメントの改善など、あなたの助けは大変ありがたいです。

- 📋 **課題**: [GitHub Issues](https://github.com/MiroMindAI/MiroFlow/issues)でバグを報告するか機能をリクエスト
- 🔀 **プルリクエスト**: プルリクエストで改善を提出
- 💬 **ディスカッション**: 質問や議論のために[Discordコミュニティ](https://discord.com/invite/GPqEnkzQZd)に参加

## ❓ よくある質問

<details>
<summary><strong>どのAPIキーが必要ですか？</strong></summary>
<br>
開始するのに必要なのはOpenRouter APIキーだけです。OpenRouterは単一のAPIを通じて複数の言語モデルへのアクセスを提供します。
</details>

<details>
<summary><strong>OpenRouter以外の言語モデルを使用できますか？</strong></summary>
<br>
はい、MiroFlowは様々な言語モデルをサポートしています。設定の詳細についてはドキュメントを確認してください。
</details>

<details>
<summary><strong>ベンチマーク結果を再現するにはどうすればよいですか？</strong></summary>
<br>
ステップバイステップの再現ガイドについては、詳細な<a href="https://miromindai.github.io/MiroFlow/evaluation_overview/">ベンチマークドキュメント</a>に従ってください。
</details>

<details>
<summary><strong>商用サポートは利用できますか？</strong></summary>
<br>
商用問い合わせとエンタープライズサポートについては、<a href="https://miromind.ai/">ウェブサイト</a>からお問い合わせください。
</details>

## 📄 ライセンス・サポート

このプロジェクトはApache License 2.0の下でライセンスされています。

<div align="center">
    <img src="https://api.star-history.com/svg?repos=MiroMindAI/MiroFlow&type=Date" alt="Star履歴チャート" height="300">
</div>

### 参考文献

技術レポートは近日公開予定！

```
@misc{2025mirothinker,
    title={MiroFlow: An Open-Source Agentic Framework for Deep Research},
    author={MiroMind AI Team},
    howpublished={\url{https://github.com/MiroMindAI/MiroFlow}},
    year={2025}
}
```

## 👥 謝辞・貢献者

- **ベンチマーク貢献者** 包括的な評価データセットを提供
- **オープンソースコミュニティ** これを可能にするツールとライブラリを提供

MiroFlowをより良くするのに貢献してくれたすべての貢献者に感謝します：

<a href="https://github.com/MiroMindAI/MiroFlow/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=MiroMindAI/MiroFlow" />
</a>

コミュニティに参加して、AIエージェントの未来を構築するのを手伝ってください！
