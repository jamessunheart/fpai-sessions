"""
Integrated Dashboard - Treasury + Delegation + AI Services
Real-time view of the complete Sacred Loop
"""

import streamlit as st
import pandas as pd
import json
from pathlib import Path
import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent))

from sacred_loop import SacredLoop
from credential_vault import CredentialVault, SpendingMonitor
from upwork_recruiter import TaskDelegator


def main():
    st.set_page_config(
        page_title="Sacred Loop Dashboard",
        page_icon="🔄",
        layout="wide"
    )

    st.title("🔄 The Sacred Loop - Integrated Dashboard")
    st.caption("AI Services → Revenue → Treasury + Delegation → Scale → Repeat")

    # Initialize systems
    loop = SacredLoop()
    vault = CredentialVault()
    spending = SpendingMonitor()

    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔄 Loop Overview",
        "💰 Treasury",
        "🤖 Delegation",
        "📊 Services",
        "📈 Projections"
    ])

    # TAB 1: LOOP OVERVIEW
    with tab1:
        st.header("The Sacred Loop")

        # Visual flow
        st.markdown("""
        ```
        AI Services ($2,500-$15,000 per customer)
                        ↓
        Revenue Split: 60% Treasury | 40% Reinvest
                ↓                           ↓
        Treasury (DeFi)              Reinvestment Pool
        25% APY yields               (VAs, Ads, Tools)
                ↓                           ↓
        Compound Growth              Faster Execution
                ↓                           ↓
                ↓_____More Customers_______↓
                        ↓
                EXPONENTIAL SCALING
        ```
        """)

        # Key metrics
        treasury = loop.get_treasury_balance()
        reinvest = loop.get_reinvestment_balance()
        revenues = json.loads(loop.revenue_log.read_text())

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            total_rev = sum(r["amount"] for r in revenues) if revenues else 0
            st.metric("Total Revenue", f"${total_rev:,.2f}")

        with col2:
            st.metric(
                "Treasury Balance",
                f"${treasury['principal']:,.2f}",
                delta=f"+${treasury['projected_monthly_yield']:,.2f}/mo"
            )

        with col3:
            st.metric(
                "Reinvestment Pool",
                f"${reinvest['available']:,.2f}"
            )

        with col4:
            total_capital = treasury['principal'] + reinvest['available']
            st.metric("Total Capital", f"${total_capital:,.2f}")

        # Loop health
        health = loop._calculate_loop_health()

        st.subheader("Loop Health")

        if health['status'] == 'starting':
            st.info("🌱 Loop starting - awaiting first customer")
        elif health['status'] == 'healthy':
            st.success(f"🔥 Loop healthy - Revenue growing {health['revenue_growth_pct']:+.1f}%")
        else:
            st.warning("⚠️ Loop needs attention")

        # Recent activity
        st.subheader("Recent Activity")

        if revenues:
            recent_df = pd.DataFrame(revenues[-10:])
            recent_df['timestamp'] = pd.to_datetime(recent_df['timestamp']).dt.strftime('%Y-%m-%d %H:%M')
            st.dataframe(
                recent_df[['timestamp', 'service', 'customer', 'amount', 'net_revenue']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No revenue yet - launch your first service!")

    # TAB 2: TREASURY
    with tab2:
        st.header("💰 Treasury Management")

        treasury = loop.get_treasury_balance()

        col1, col2 = st.columns(2)

        with col1:
            st.metric("Principal", f"${treasury['principal']:,.2f}")
            st.metric("APY", f"{treasury['apy']*100:.1f}%")

        with col2:
            st.metric(
                "Monthly Yield",
                f"${treasury['projected_monthly_yield']:,.2f}"
            )
            st.metric(
                "Annual Yield",
                f"${treasury['projected_annual_yield']:,.2f}"
            )

        # Treasury deployments
        st.subheader("Deployment History")

        treasury_log = json.loads(loop.treasury_log.read_text())

        if treasury_log:
            df = pd.DataFrame(treasury_log)
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d')
            st.dataframe(
                df[['timestamp', 'amount', 'source', 'expected_apy']],
                use_container_width=True,
                hide_index=True
            )

            # Cumulative treasury growth
            df_full = pd.DataFrame(treasury_log)
            df_full['cumulative'] = df_full['amount'].cumsum()
            st.line_chart(df_full['cumulative'])
        else:
            st.info("No treasury deployments yet")

        # Treasury strategy reminder
        with st.expander("📖 Treasury Strategy"):
            st.markdown("""
            **Dynamic Allocation Strategy** (from TREASURY_DYNAMIC_STRATEGY.md)

            - **60% Base Yield:** Aave, Pendle, Curve (8% APY)
            - **40% Tactical:** Quarterly expiries, cycle timing (40% APY)
            - **Blended Target:** 25% APY

            **Current Market Position:**
            - MVRV Z-Score: 2.43 (mid-cycle)
            - Days to peak: 140-150 (Feb-March 2026)
            - Next quarterly expiry: December 27, 2025

            **Risk Management:**
            - Max allocation per protocol: 25%
            - Diversification across 4+ protocols
            - Weekly rebalancing
            - Stop-loss at MVRV 5.0
            """)

    # TAB 3: DELEGATION
    with tab3:
        st.header("🤖 Delegation & Reinvestment")

        reinvest = loop.get_reinvestment_balance()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("Available", f"${reinvest['available']:,.2f}")

        with col2:
            st.metric("Total Allocated", f"${reinvest['total_allocated']:,.2f}")

        with col3:
            st.metric("Total Spent", f"${reinvest['total_spent']:,.2f}")

        # Spending by category
        if reinvest['spending_by_category']:
            st.subheader("Spending by Category")

            spending_df = pd.DataFrame([
                {"Category": k, "Amount": v}
                for k, v in reinvest['spending_by_category'].items()
            ])

            st.bar_chart(spending_df.set_index('Category'))

        # Reinvestment log
        st.subheader("Reinvestment History")

        reinvest_log = json.loads(loop.reinvest_log.read_text())

        if reinvest_log:
            df = pd.DataFrame(reinvest_log)
            df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d')
            df['type'] = df['amount'].apply(lambda x: 'Allocation' if x > 0 else 'Spend')
            df['amount_abs'] = df['amount'].abs()

            st.dataframe(
                df[['timestamp', 'type', 'amount_abs', 'source']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No reinvestment activity yet")

        # Delegation opportunities
        with st.expander("💡 What to Delegate"):
            st.markdown("""
            **High-ROI Delegation Opportunities:**

            1. **Account Setups** ($50 each, saves 30 min)
               - Stripe account + API keys
               - Facebook Ads account + pixel
               - Google Ads account
               - Calendly + Zapier integration

            2. **Landing Page Deployment** ($75, saves 1 hour)
               - v0.dev → Vercel deployment
               - Custom domain setup
               - SSL certificate

            3. **Ad Campaign Management** ($100/week, saves 2 hours)
               - Daily budget optimization
               - A/B testing
               - Performance reporting

            4. **Customer Support** ($15/hour, infinite scaling)
               - Initial consultation scheduling
               - Document delivery
               - Follow-up emails

            **ROI Formula:**
            - Your time: $100/hour
            - VA cost: $15-50/hour
            - Savings: $50-85/hour
            - Scale: Unlimited parallel execution
            """)

    # TAB 4: SERVICES
    with tab4:
        st.header("📊 AI Services Performance")

        revenues = json.loads(loop.revenue_log.read_text())

        if revenues:
            # Service breakdown
            by_service = {}
            for r in revenues:
                service = r['service']
                if service not in by_service:
                    by_service[service] = {
                        'count': 0,
                        'revenue': 0,
                        'net': 0
                    }
                by_service[service]['count'] += 1
                by_service[service]['revenue'] += r['amount']
                by_service[service]['net'] += r['net_revenue']

            # Display metrics
            st.subheader("Service Performance")

            service_df = pd.DataFrame([
                {
                    "Service": k,
                    "Customers": v['count'],
                    "Revenue": f"${v['revenue']:,.2f}",
                    "Avg/Customer": f"${v['revenue']/v['count']:,.2f}"
                }
                for k, v in by_service.items()
            ])

            st.dataframe(service_df, use_container_width=True, hide_index=True)

            # Revenue over time
            st.subheader("Revenue Over Time")

            revenue_df = pd.DataFrame(revenues)
            revenue_df['date'] = pd.to_datetime(revenue_df['timestamp']).dt.date
            daily_revenue = revenue_df.groupby('date')['amount'].sum()

            st.line_chart(daily_revenue)

        else:
            st.info("No service revenue yet - launch your first offer!")

            st.markdown("""
            **Available Services:**

            1. **Church Formation** ($2,500 - $15,000)
               - Basic: $2,500 (documents only)
               - Full: $15,000 (with legal review)
               - Target: Freedom-seeking entrepreneurs

            2. **Custom GPTs** ($2,000 - $10,000)
               - Customer support bots
               - Internal knowledge bases
               - Process automation
               - Target: SaaS companies, service businesses

            3. **I MATCH** (20% commission)
               - AI-powered matching service
               - Research + curation
               - Facilitated introductions
               - Target: Anyone needing expert services
            """)

    # TAB 5: PROJECTIONS
    with tab5:
        st.header("📈 Growth Projections")

        # Projection parameters
        col1, col2, col3 = st.columns(3)

        with col1:
            customers_per_month = st.slider(
                "Customers/Month (Month 1)",
                min_value=1,
                max_value=50,
                value=5
            )

        with col2:
            avg_revenue = st.slider(
                "Avg Revenue/Customer",
                min_value=1000,
                max_value=15000,
                value=3500,
                step=500
            )

        with col3:
            months = st.slider(
                "Projection Period (months)",
                min_value=3,
                max_value=24,
                value=12
            )

        # Generate projection
        projections = loop.project_growth(
            months=months,
            customers_per_month=customers_per_month,
            avg_revenue_per_customer=avg_revenue
        )

        # Display chart
        st.subheader("Capital Growth Projection")

        proj_df = pd.DataFrame(projections)
        st.line_chart(proj_df.set_index('month')[['treasury_balance', 'reinvest_pool', 'total_capital']])

        # Key milestones
        st.subheader("Key Milestones")

        final = projections[-1]

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                f"Month {months} Total Capital",
                f"${final['total_capital']:,.2f}"
            )

        with col2:
            st.metric(
                f"Month {months} Treasury",
                f"${final['treasury_balance']:,.2f}",
                delta=f"+${final['treasury_monthly_yield']:,.2f}/mo yield"
            )

        with col3:
            st.metric(
                f"Month {months} Customer Velocity",
                f"{final['customers']}/month"
            )

        # Projection table
        with st.expander("📊 Detailed Projections"):
            proj_display = proj_df[[
                'month', 'customers', 'monthly_revenue',
                'treasury_balance', 'reinvest_pool', 'total_capital'
            ]].copy()

            # Format currency
            for col in ['monthly_revenue', 'treasury_balance', 'reinvest_pool', 'total_capital']:
                proj_display[col] = proj_display[col].apply(lambda x: f"${x:,.2f}")

            st.dataframe(proj_display, use_container_width=True, hide_index=True)

        # Assumptions
        with st.expander("📖 Projection Assumptions"):
            st.markdown(f"""
            **Revenue Assumptions:**
            - Starting customers: {customers_per_month}/month
            - Avg revenue/customer: ${avg_revenue:,.2f}
            - Fulfillment cost: 15% (VAs, tools)
            - Net margin: 85%

            **Capital Allocation:**
            - Treasury: 60% of net revenue
            - Reinvestment: 40% of net revenue

            **Treasury Yields:**
            - Base APY: 8% (conservative DeFi)
            - Tactical APY: 40% (quarterly plays)
            - Blended APY: 25% (realistic)
            - Compounding: Monthly

            **Scaling Dynamics:**
            - Velocity multiplier: +5% capacity per $1K reinvested
            - Growth cap: 20% per month (realistic constraint)
            - Reinvestment → More VAs → Faster delivery → More customers

            **Result:**
            - Exponential compounding from multiple sources:
              1. Treasury yields (25% APY)
              2. Reinvestment velocity (5% per $1K)
              3. Customer word-of-mouth (organic growth)
            """)


if __name__ == "__main__":
    main()
