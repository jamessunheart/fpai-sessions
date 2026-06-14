# 🎯 MISSION M013: Spec for Treasury Arena

**Status:** 🟡 OPEN  
**Created:** 2025-11-23  
**Estimated Time:** TBD (see spec below)  
**Difficulty:** TBD (see spec below)

---

## 🚀 QUICK START FOR BUILDERS

**This is a ready-to-code mission.** Everything you need is in this file.

### 📦 STARTER KIT

Before you start coding, set up your foundation:

1. **Create a New Repository**
   ```bash
   mkdir mission-m013
   cd mission-m013
   git init
   ```

2. **Copy Foundation Files**
   
   You'll need these files from the Full Potential AI codebase:
   
   - `TECH_STACK.md` - Technology standards to follow
   - `UDC_COMPLIANCE.md` - Required endpoints (if building a service)
   - `.env.example` - Environment variable template
   
   Copy them from: `https://github.com/fullpotentialai/fpai-cockpit/tree/main/docs/architecture/foundation`

3. **Set Up Your Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Build According to Spec**
   
   Follow the detailed specification below. It includes:
   - Complete architecture
   - API endpoints
   - Database schemas
   - Testing requirements
   - Everything you need!

5. **Test Locally**
   ```bash
   # Run tests
   pytest tests/ -v
   
   # Start the service (if applicable)
   uvicorn app.main:app --reload
   
   # Test the endpoints
   curl http://localhost:8000/health
   ```

6. **Submit Your Work**
   
   When complete:
   - Push your code to GitHub (or your preferred platform)
   - Test that all requirements are met
   - Submit your repo URL: https://fullpotential.ai/feedback
   - Include: Your name, Mission ID (M013), and any notes

---

## 📝 TECHNICAL SPECIFICATION

# Treasury Arena

- **Priority:** P1 (High/Core)
- **Constitution Principle:** **Optimization over Extraction**
- **Regenerative Impact:** Transforms idle capital into active, yield-generating resources for the ecosystem. By automating asset management and yield farming strategies, it ensures resources multiply rather than stagnate.

## 1. 📋 OVERVIEW
The Treasury Arena (`treasury-arena`) is the financial engine of the ecosystem. It manages crypto assets, executes yield strategies (via Solana/DeFi integrations), tracks portfolio performance in real-time, and reports financial health to the Dashboard. It acts as the "Bank" and "Investment Manager" combined.

- **Business Value:** Generates passive income (targeting 20-50% APY) to fund operations and research.
- **User Impact:** Provides transparency on ecosystem financial health; no direct user interaction for general users.
- **Timeline:** 4-5 days.
- **Complexity:** High (Blockchain integration, Security critical).

## 2. 🎯 REQUIREMENTS
- **Functional:**
  - Track balances across multiple wallets (Solana, potentially others).
  - Execute swap/stake operations via Jupiter/Raydium APIs (automated or semi-automated).
  - Calculate real-time APY, PnL, and total value locked (TVL).
  - Expose financial metrics to `dashboard`.
  - Alert on significant price movements or strategy health variations.
- **Non-Functional:**
  - UDC Compliant.
  - Security: **CRITICAL**. Private keys must never be exposed or logged. Use secure vault integration.
  - Latency: Real-time price updates (< 1 min lag).
  - Reliability: Failsafe mechanisms to prevent unauthorized withdrawals.

## 3. 🏗️ ARCHITECTURE
- **Components:**
  - **Wallet Manager:** Interface to blockchain nodes/RPCs.
  - **Strategy Engine:** Logic for asset allocation (e.g., "Keep 50% in SOL, 50% in Stablecoins").
  - **Market Data Feeder:** Fetches prices from CoinGecko/Birdeye.
  - **Transaction Executor:** Signs and broadcasts transactions.
- **Data Flow:**
  1. `Market Data Feeder` updates `Asset` prices.
  2. `Strategy Engine` evaluates current allocation vs target.
  3. If rebalance needed -> Generate Transaction.
  4. `Transaction Executor` signs (using secure key provider) and broadcasts.
  5. `Wallet Manager` monitors confirmation and updates balances.
- **Integration:**
  - Solana RPC nodes (Helius/QuickNode).
  - Jupiter API (Aggregator).
  - `registry` / `dashboard`.

## 4. 🔌 API SPECIFICATION
Base URL: `/api/v1`

- `GET /portfolio`: Get current holdings and total value.
- `GET /performance`: Get historical PnL and APY.
- `POST /strategies/{id}/execute`: Trigger a specific strategy run (Auth required).
- `GET /history`: List past transactions.

**UDC Endpoints:**
- `GET /health` (Check RPC connection)
- `GET /capabilities`
- `GET /state` (Current TVL, Active Strategies)
- `GET /dependencies`
- `POST /message`

## 5. 💾 DATABASE DESIGN
**Tables (PostgreSQL):**

- **assets**
  - `symbol` (String, PK)
  - `name` (String)
  - `contract_address` (String)
  - `decimals` (Integer)

- **balances**
  - `id` (UUID, PK)
  - `asset_symbol` (String, FK)
  - `amount` (Decimal)
  - `wallet_address` (String)
  - `updated_at` (Timestamp)

- **transactions**
  - `tx_hash` (String, PK)
  - `type` (Enum: SWAP, STAKE, TRANSFER)
  - `asset_in` (String)
  - `amount_in` (Decimal)
  - `asset_out` (String)
  - `amount_out` (Decimal)
  - `status` (Enum: CONFIRMED, FAILED, PENDING)
  - `timestamp` (Timestamp)

- **snapshots** (Time-series for charts)
  - `timestamp` (Timestamp, PK)
  - `total_value_usd` (Decimal)
  - `pnl_24h` (Decimal)

## 6. 🎨 UI/UX REQUIREMENTS
- **Dashboard Widget:** Mini-graph of TVL and current APY.
- **Detailed View:** Table of assets, allocation pie chart, transaction history log.

## 7. 🔐 SECURITY CONSIDERATIONS
- **Key Management:** Private keys MUST be loaded from environment variables or a secure vault (e.g., HashiCorp Vault) at startup. NEVER stored in DB or code.
- **Spending Limits:** Hardcoded daily withdrawal limits.
- **Address Whitelisting:** Only allow transfers to known internal wallets.

## 8. ✅ TESTING STRATEGY
- **Unit Tests:**
  - Test allocation logic (math verification).
  - Test transaction builder (instruction correctness).
- **Integration Tests:**
  - Use Solana **Devnet** for all transaction tests.
  - Mock price feeds to test strategy triggers.
- **Security Audit:**
  - Static analysis (Bandit) for key leaks.
  - Manual review of transaction signing code.

## 9. 📦 DEPLOYMENT PLAN
- **Docker:** Python 3.11 slim.
- **Env Vars:**
  - `SOLANA_RPC_URL`
  - `WALLET_PRIVATE_KEY` (Secret!)
  - `DATABASE_URL`
  - `PRICE_API_KEY`

## 10. 🛠️ BUILDER INSTRUCTIONS
1. Clone repo and `cd treasury-arena`.
2. `python3 -m venv venv && source venv/bin/activate`.
3. `pip install -r requirements.txt` (include `solana`, `solders`).
4. Configure `.env` with a **Devnet** wallet key.
5. Run `python scripts/fund_devnet.py` (to airdrop SOL).
6. `uvicorn app.main:app --reload`.
7. Test `/portfolio` endpoint.

---

## 💬 GETTING HELP
**Stuck?** Don't struggle alone!
- **Ask Questions:** https://fullpotential.ai/feedback
- **Report Issues:** Same form, tell us what's blocking you
- **Suggest Improvements:** If the spec is unclear, let us know

**Your feedback makes the system better for everyone.**

---

## ✅ COMPLETION CHECKLIST
Before submitting, verify:
- [ ] All requirements implemented
- [ ] Tests passing (>80% coverage)
- [ ] Code follows TECH_STACK.md standards
- [ ] UDC endpoints implemented
- [ ] README.md with setup instructions
- [ ] Environment variables documented
- [ ] Local testing successful (on Devnet)
- [ ] Code committed to repository

---

## 🎓 WHAT YOU'LL LEARN
By completing this mission:
- Blockchain interaction with Python (Solana).
- Financial data modeling.
- High-security application design.
- Automated trading logic.

---

**Original Idea:** "Spec for Treasury Arena"  
**Mission ID:** M013  
**Generated:** 2025-11-23

🚀 **Let's build something awesome!**

