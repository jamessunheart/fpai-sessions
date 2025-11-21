"""
Delegation System Monitoring Dashboard
Real-time monitoring of credentials, spending, tasks, and security
"""

import streamlit as st
import json
import datetime
from pathlib import Path
import pandas as pd
from typing import Dict, List
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from credential_vault import CredentialVault, SpendingMonitor


def load_task_log() -> List[Dict]:
    """Load task delegation log"""
    task_log_path = Path("/root/delegation-system/upwork-api/task_log.json")
    if task_log_path.exists():
        return json.loads(task_log_path.read_text())
    return []


def load_jobs_log() -> List[Dict]:
    """Load Upwork jobs log"""
    jobs_log_path = Path("/root/delegation-system/upwork-api/jobs_log.json")
    if jobs_log_path.exists():
        return json.loads(jobs_log_path.read_text())
    return []


def main():
    st.set_page_config(
        page_title="Delegation System Monitor",
        page_icon="🔒",
        layout="wide"
    )

    st.title("🔒 Delegation System Monitor")
    st.caption("Real-time monitoring of credentials, spending, and VA tasks")

    # Initialize systems
    vault = CredentialVault()
    spending = SpendingMonitor()

    # Create tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Overview",
        "🔐 Credential Access",
        "💳 Spending",
        "📋 Tasks",
        "⚠️ Security Alerts"
    ])

    # TAB 1: OVERVIEW
    with tab1:
        col1, col2, col3, col4 = st.columns(4)

        # Spending 24h
        spending_24h = spending.get_spending_24h()
        with col1:
            st.metric(
                "24h Spending",
                f"${spending_24h:.2f}",
                delta=f"-${5000 - spending_24h:.2f} budget remaining",
                delta_color="inverse"
            )

        # Active tasks
        tasks = load_task_log()
        active_tasks = [t for t in tasks if t['status'] in ['pending', 'job_posted', 'in_progress']]
        with col2:
            st.metric("Active Tasks", len(active_tasks))

        # Credential accesses (24h)
        access_log = vault.get_access_log(hours=24)
        with col3:
            st.metric("Credential Access (24h)", len(access_log))

        # Security alerts
        suspicious = vault.get_suspicious_activity()
        spending_alerts = spending.check_alerts({
            "daily": 500,
            "category_tools": 200,
            "category_services": 300
        })
        total_alerts = len(suspicious) + len(spending_alerts)
        with col4:
            st.metric(
                "Security Alerts",
                total_alerts,
                delta="🟢 All clear" if total_alerts == 0 else "⚠️ Review needed",
                delta_color="inverse" if total_alerts == 0 else "normal"
            )

        # Recent Activity
        st.subheader("Recent Activity")

        # Combine recent credential access and tasks
        recent_activity = []

        for log in access_log[-5:]:
            recent_activity.append({
                "timestamp": log["timestamp"],
                "type": "Credential Access",
                "description": f"{log['requester']} accessed {log['service']} ({log['action']})",
                "status": "🟢" if log['action'] == "READ" else "🔴" if log['action'] == "DENIED" else "🟡"
            })

        for task in tasks[-5:]:
            recent_activity.append({
                "timestamp": task["created_at"],
                "type": "Task",
                "description": task["description"][:60] + "...",
                "status": "🟢" if task['status'] == 'completed' else "🟡"
            })

        # Sort by timestamp
        recent_activity.sort(key=lambda x: x["timestamp"], reverse=True)

        if recent_activity:
            df = pd.DataFrame(recent_activity[:10])
            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No recent activity")

    # TAB 2: CREDENTIAL ACCESS
    with tab2:
        st.subheader("Credential Access Log (Last 24 Hours)")

        access_log = vault.get_access_log(hours=24)

        if access_log:
            df = pd.DataFrame(access_log)

            # Format timestamp
            df['time'] = pd.to_datetime(df['timestamp']).dt.strftime('%H:%M:%S')

            # Color code by action
            def color_action(val):
                if val == "READ":
                    return "🟢 " + val
                elif val == "DENIED":
                    return "🔴 " + val
                elif val == "WRITE":
                    return "🟡 " + val
                else:
                    return "⚪ " + val

            df['action'] = df['action'].apply(color_action)

            # Display
            st.dataframe(
                df[['time', 'requester', 'service', 'action', 'purpose']],
                use_container_width=True,
                hide_index=True
            )

            # Summary stats
            col1, col2, col3 = st.columns(3)

            with col1:
                total_access = len(access_log)
                st.metric("Total Access", total_access)

            with col2:
                denied = len([a for a in access_log if a['action'] == 'DENIED'])
                st.metric("Denied Access", denied, delta="⚠️ Security event" if denied > 0 else None)

            with col3:
                unique_requesters = len(set([a['requester'] for a in access_log]))
                st.metric("Unique Requesters", unique_requesters)

        else:
            st.info("No credential access in last 24 hours")

        # Available credentials
        st.subheader("Available Credentials by Tier")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**Tier 1: Critical** 🔐")
            tier1 = vault.list_credentials("1")
            if tier1:
                for cred in tier1:
                    st.text(f"• {cred}")
            else:
                st.caption("No credentials")

        with col2:
            st.markdown("**Tier 2: Monitored** 🔑")
            tier2 = vault.list_credentials("2")
            if tier2:
                for cred in tier2:
                    st.text(f"• {cred}")
            else:
                st.caption("No credentials")

        with col3:
            st.markdown("**Tier 3: Delegated** 🗝️")
            tier3 = vault.list_credentials("3")
            if tier3:
                for cred in tier3:
                    st.text(f"• {cred}")
            else:
                st.caption("No credentials")

    # TAB 3: SPENDING
    with tab3:
        st.subheader("Operations Card Spending")

        # 24-hour spending
        spending_24h = spending.get_spending_24h()

        col1, col2 = st.columns(2)

        with col1:
            st.metric("24h Spending", f"${spending_24h:.2f}")
            st.progress(min(spending_24h / 5000, 1.0))
            st.caption(f"${5000 - spending_24h:.2f} remaining (${5000} daily limit)")

        with col2:
            # Spending by category
            by_category = spending.get_spending_by_category(hours=24)
            if by_category:
                st.bar_chart(by_category)
            else:
                st.info("No spending in last 24 hours")

        # Spending alerts
        alerts = spending.check_alerts({
            "daily": 500,
            "category_tools": 200,
            "category_services": 300
        })

        if alerts:
            st.subheader("⚠️ Spending Alerts")
            for alert in alerts:
                st.warning(f"**{alert['type']}**: ${alert['amount']:.2f} (threshold: ${alert['threshold']:.2f})")

        # Weekly breakdown
        st.subheader("7-Day Spending Breakdown")
        weekly_by_cat = spending.get_spending_by_category(hours=168)

        if weekly_by_cat:
            df = pd.DataFrame([
                {"Category": k, "Amount": v}
                for k, v in weekly_by_cat.items()
            ])
            st.dataframe(df, use_container_width=True, hide_index=True)

            total_weekly = sum(weekly_by_cat.values())
            st.metric("7-Day Total", f"${total_weekly:.2f}")
        else:
            st.info("No spending in last 7 days")

    # TAB 4: TASKS
    with tab4:
        st.subheader("Delegated Tasks")

        tasks = load_task_log()
        jobs = load_jobs_log()

        if tasks:
            # Task status summary
            col1, col2, col3, col4 = st.columns(4)

            pending = len([t for t in tasks if t['status'] == 'pending'])
            posted = len([t for t in tasks if t['status'] == 'job_posted'])
            in_progress = len([t for t in tasks if t['status'] == 'in_progress'])
            completed = len([t for t in tasks if t['status'] == 'completed'])

            with col1:
                st.metric("Pending", pending)
            with col2:
                st.metric("Job Posted", posted)
            with col3:
                st.metric("In Progress", in_progress)
            with col4:
                st.metric("Completed", completed)

            # Task list
            st.subheader("Task List")

            for task in reversed(tasks[-10:]):
                with st.expander(f"{task['id']} - {task['description'][:50]}..."):
                    st.text(f"Type: {task['type']}")
                    st.text(f"Status: {task['status']}")
                    st.text(f"Budget: ${task['budget']}")
                    st.text(f"Deadline: {task['deadline']}")
                    st.text(f"Created: {task['created_at']}")

                    if 'job_id' in task:
                        st.text(f"Job ID: {task['job_id']}")

        else:
            st.info("No tasks delegated yet")

        # Upwork jobs
        if jobs:
            st.subheader("Upwork Jobs Posted")

            for job in reversed(jobs[-5:]):
                with st.expander(f"{job['title']}"):
                    st.text(f"Budget: ${job['budget']}")
                    st.text(f"Posted: {job['posted_at']}")
                    st.text(f"Status: {job['status']}")
                    st.markdown("**Description:**")
                    st.text(job['description'][:200] + "...")

    # TAB 5: SECURITY ALERTS
    with tab5:
        st.subheader("🔒 Security Monitoring")

        # Suspicious activity
        suspicious = vault.get_suspicious_activity()

        if suspicious:
            st.warning(f"⚠️ {len(suspicious)} suspicious activity detected")

            for alert in suspicious:
                with st.expander(f"{alert['type']} - {alert.get('count', 'N/A')} events"):
                    st.json(alert)
        else:
            st.success("✅ No suspicious activity detected")

        # Spending alerts
        spending_alerts = spending.check_alerts({
            "daily": 500,
            "category_tools": 200,
            "category_services": 300
        })

        if spending_alerts:
            st.warning(f"⚠️ {len(spending_alerts)} spending alerts")

            for alert in spending_alerts:
                st.warning(f"**{alert['type']}**: ${alert['amount']:.2f} exceeds ${alert['threshold']:.2f}")
        else:
            st.success("✅ Spending within normal limits")

        # Recent denied access
        denied_access = [log for log in vault.get_access_log(hours=24) if log['action'] == 'DENIED']

        if denied_access:
            st.subheader("🔴 Denied Access Attempts (24h)")

            df = pd.DataFrame(denied_access)
            st.dataframe(
                df[['timestamp', 'requester', 'service', 'purpose']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.success("✅ No denied access attempts")

        # Security recommendations
        st.subheader("Security Recommendations")

        recommendations = []

        # Check for high access volume
        access_log = vault.get_access_log(hours=24)
        if len(access_log) > 50:
            recommendations.append("⚠️ High credential access volume (>50 in 24h). Review access patterns.")

        # Check spending
        if spending_24h > 500:
            recommendations.append("⚠️ High spending detected. Review transaction logs.")

        # Check denied access
        if denied_access:
            recommendations.append(f"⚠️ {len(denied_access)} denied access attempts. Investigate unauthorized access.")

        if recommendations:
            for rec in recommendations:
                st.warning(rec)
        else:
            st.success("✅ All security metrics within normal parameters")

        # Auto-refresh
        st.caption("Auto-refreshing every 30 seconds...")
        st.button("🔄 Refresh Now", key="refresh")


if __name__ == "__main__":
    main()
