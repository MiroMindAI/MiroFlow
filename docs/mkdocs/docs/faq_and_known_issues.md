## FAQ

**Q: What is the estimated cost of running the GAIA validation set for a single run?** <br>
**A**: The cost is approximately **$250 USD** for a run with cache.

**Q: How long does it take to run the GAIA validation set for a single run?** <br>
**A**: With the `max_concurrent` parameter set to 20, a full run takes about **2 hours** to complete.

**Q: Are all the specified APIs required?** <br>
**A**: **Yes.** To fully reproduce our published results, access to all the listed APIs in corresponding benchmark is necessary.


**Q: What is the difference between MiroFlow and MiroThinker?** <br>
**A**:  **MiroFlow** is primarily focused on interacting with proprietary models; **MiroThinker** is designed for our own open-source models.

We plan to merge these two projects in the future to create a single, unified platform.


## Known Issues & Roadmap

### ✅ Recently Completed
- **FutureX Benchmark**: Full support for FutureX future prediction benchmark evaluation
- **FRAMES Benchmark**: Added FRAMES-Test benchmark evaluation
- **New Tools**: Added `tool-code-sandbox`, `tool-jina-scrape`, and `tool-serper-search`
- **New LLM Clients**: Added `OpenRouterClient` and `OpenAIClient` for generic API access

### 🔄 Currently in Development
- **Token Usage & Cost Tracking**: Implementing detailed usage analytics and cost calculation features

---
**Last Updated:** Feb 2026
**Doc Contributor:** Team @ MiroMind AI