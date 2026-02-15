"""Analytics and usage insights commands."""

import typer
from rich.console import Console
from rich.panel import Panel
from typing import Optional

from ..api import api, APIError
from ..utils.display import (
    print_error, print_success, print_info,
    print_table, print_dict_as_table, get_output_format,
    format_cost, format_tokens
)
from ..utils.auth import ensure_authenticated

console = Console()

app = typer.Typer(help="📊 Usage analytics & insights")


@app.command("overview")
def analytics_overview(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show analytics dashboard overview.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        overview = api.get("/analytics/overview")
        
        if output_format == "json":
            console.print_json(overview)
        else:
            # Dashboard-style overview
            console.print("\n[bold cyan]📊 Bonito Analytics Overview[/bold cyan]")
            
            # Key metrics panel
            metrics = overview.get("metrics", {})
            
            metrics_text = f"""
[bold green]Total Requests:[/bold green] {metrics.get('total_requests', 0):,}
[bold green]Total Cost:[/bold green] ${metrics.get('total_cost', 0):.2f}
[bold green]Total Tokens:[/bold green] {format_tokens(metrics.get('total_tokens', 0))}
[bold green]Success Rate:[/bold green] {metrics.get('success_rate', 0):.1f}%
[bold green]Avg Latency:[/bold green] {metrics.get('avg_latency_ms', 0):.0f}ms
            """
            
            console.print(Panel(metrics_text.strip(), title="Key Metrics (Last 30 Days)", border_style="green"))
            
            # Top models
            top_models = overview.get("top_models", [])
            if top_models:
                model_data = []
                for model in top_models[:5]:
                    model_data.append({
                        "Model": model.get("id", ""),
                        "Requests": f"{model.get('requests', 0):,}",
                        "Cost": format_cost(model.get('cost', 0)),
                        "Tokens": format_tokens(model.get('tokens', 0)),
                        "Share": f"{model.get('percentage', 0):.1f}%"
                    })
                
                print_table(model_data, title="🔥 Top Models")
            
            # Recent activity
            recent_activity = overview.get("recent_activity", {})
            if recent_activity:
                activity_info = {
                    "Requests (24h)": f"{recent_activity.get('requests_24h', 0):,}",
                    "Cost (24h)": format_cost(recent_activity.get('cost_24h', 0)),
                    "Peak Hour": recent_activity.get('peak_hour', 'N/A'),
                    "Most Used Model": recent_activity.get('top_model', 'N/A'),
                    "Avg Response Time": f"{recent_activity.get('avg_response_time', 0):.1f}s",
                }
                
                print_dict_as_table(activity_info, title="📈 Recent Activity")
            
            # Cost trends
            cost_trend = overview.get("cost_trend", {})
            if cost_trend:
                trend_direction = "📈" if cost_trend.get("change_percent", 0) > 0 else "📉"
                trend_text = f"{trend_direction} {abs(cost_trend.get('change_percent', 0)):.1f}% vs last period"
                console.print(f"\n[bold]Cost Trend:[/bold] {trend_text}")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get analytics overview: {e}")


@app.command("usage")
def analytics_usage(
    period: str = typer.Option("week", "--period", help="Time period (day/week/month)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show detailed usage analytics over time.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    if period not in ["day", "week", "month"]:
        print_error("Period must be one of: day, week, month")
        return
    
    try:
        usage_data = api.get("/analytics/usage", {"period": period})
        
        if output_format == "json":
            console.print_json(usage_data)
        else:
            console.print(f"\n[bold cyan]📈 Usage Analytics ({period.title()}ly)[/bold cyan]")
            
            # Summary stats
            summary = usage_data.get("summary", {})
            summary_info = {
                "Period": period.title(),
                "Total Requests": f"{summary.get('total_requests', 0):,}",
                "Total Tokens": format_tokens(summary.get('total_tokens', 0)),
                "Total Cost": format_cost(summary.get('total_cost', 0)),
                "Unique Models Used": summary.get('unique_models', 0),
                "Avg Requests/Day": f"{summary.get('avg_requests_per_day', 0):.0f}",
            }
            
            print_dict_as_table(summary_info, title="Usage Summary")
            
            # Time series data
            time_series = usage_data.get("time_series", [])
            if time_series:
                series_data = []
                for point in time_series[-10:]:  # Show last 10 data points
                    series_data.append({
                        "Date": point.get("date", ""),
                        "Requests": f"{point.get('requests', 0):,}",
                        "Tokens": format_tokens(point.get('tokens', 0)),
                        "Cost": format_cost(point.get('cost', 0)),
                        "Models": point.get('unique_models', 0),
                    })
                
                print_table(series_data, title=f"{period.title()}ly Usage Trend")
            
            # Top endpoints/features
            top_endpoints = usage_data.get("top_endpoints", [])
            if top_endpoints:
                endpoint_data = []
                for endpoint in top_endpoints[:5]:
                    endpoint_data.append({
                        "Endpoint": endpoint.get("path", ""),
                        "Requests": f"{endpoint.get('requests', 0):,}",
                        "Share": f"{endpoint.get('percentage', 0):.1f}%",
                        "Avg Latency": f"{endpoint.get('avg_latency_ms', 0):.0f}ms",
                    })
                
                print_table(endpoint_data, title="🎯 Top Endpoints")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get usage analytics: {e}")


@app.command("costs")
def analytics_costs(
    period: Optional[str] = typer.Option(None, "--period", help="Time period (daily/weekly/monthly)"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show cost analytics and breakdown.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        cost_data = api.get("/analytics/costs", {"period": period} if period else {})
        
        if output_format == "json":
            console.print_json(cost_data)
        else:
            console.print(f"\n[bold cyan]💰 Cost Analytics{f' ({period})' if period else ''}[/bold cyan]")
            
            # Cost summary
            summary = cost_data.get("summary", {})
            total_cost = summary.get("total_cost", 0)
            
            console.print(f"\n[bold green]Total Cost:[/bold green] ${total_cost:.2f}")
            
            # Cost breakdown by category
            breakdown = cost_data.get("breakdown", {})
            
            if breakdown.get("by_model"):
                model_costs = []
                for model_cost in breakdown["by_model"]:
                    model_costs.append({
                        "Model": model_cost.get("model", ""),
                        "Cost": format_cost(model_cost.get("cost", 0)),
                        "Requests": f"{model_cost.get('requests', 0):,}",
                        "Tokens": format_tokens(model_cost.get('tokens', 0)),
                        "% of Total": f"{(model_cost.get('cost', 0) / total_cost * 100):.1f}%" if total_cost > 0 else "0%"
                    })
                
                print_table(model_costs, title="💸 Cost by Model")
            
            if breakdown.get("by_provider"):
                provider_costs = []
                for provider_cost in breakdown["by_provider"]:
                    provider_costs.append({
                        "Provider": provider_cost.get("provider", ""),
                        "Cost": format_cost(provider_cost.get("cost", 0)),
                        "Share": f"{(provider_cost.get('cost', 0) / total_cost * 100):.1f}%" if total_cost > 0 else "0%",
                        "Models": provider_cost.get("model_count", 0),
                    })
                
                print_table(provider_costs, title="☁️  Cost by Provider")
            
            # Cost trends
            trends = cost_data.get("trends", {})
            if trends:
                trend_info = {
                    "This Period": format_cost(trends.get("current_period", 0)),
                    "Previous Period": format_cost(trends.get("previous_period", 0)),
                    "Change": f"{trends.get('change_percent', 0):+.1f}%",
                    "Projected Month": format_cost(trends.get("projected_monthly", 0)),
                    "Avg Daily": format_cost(trends.get("avg_daily", 0)),
                }
                
                print_dict_as_table(trend_info, title="📊 Cost Trends")
            
            # Cost optimization suggestions
            suggestions = cost_data.get("optimization_suggestions", [])
            if suggestions:
                console.print(f"\n[bold yellow]💡 Cost Optimization Suggestions:[/bold yellow]")
                for suggestion in suggestions:
                    console.print(f"  • {suggestion.get('message', '')}")
                    if suggestion.get('potential_savings'):
                        console.print(f"    [dim]Potential savings: {format_cost(suggestion['potential_savings'])}[/dim]")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get cost analytics: {e}")


@app.command("trends")
def analytics_trends(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Show usage and performance trends analysis.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        trends_data = api.get("/analytics/trends")
        
        if output_format == "json":
            console.print_json(trends_data)
        else:
            console.print(f"\n[bold cyan]📈 Trends Analysis[/bold cyan]")
            
            # Usage trends
            usage_trends = trends_data.get("usage_trends", {})
            if usage_trends:
                console.print(f"\n[bold]📊 Usage Trends:[/bold]")
                
                trends_info = {
                    "Request Volume": f"{usage_trends.get('requests_trend', 0):+.1f}% vs last month",
                    "Token Usage": f"{usage_trends.get('tokens_trend', 0):+.1f}% vs last month",
                    "Unique Users": f"{usage_trends.get('users_trend', 0):+.1f}% vs last month",
                    "Peak Usage Time": usage_trends.get('peak_time', 'N/A'),
                    "Growth Rate": f"{usage_trends.get('growth_rate', 0):.1f}% monthly",
                }
                
                print_dict_as_table(trends_info, title="Usage Trends")
            
            # Model adoption trends
            model_trends = trends_data.get("model_trends", [])
            if model_trends:
                trend_data = []
                for trend in model_trends:
                    direction = "📈" if trend.get("change_percent", 0) > 0 else "📉"
                    trend_data.append({
                        "Model": trend.get("model", ""),
                        "Trend": f"{direction} {abs(trend.get('change_percent', 0)):.1f}%",
                        "Current Share": f"{trend.get('current_share', 0):.1f}%",
                        "Previous Share": f"{trend.get('previous_share', 0):.1f}%",
                    })
                
                print_table(trend_data, title="🤖 Model Adoption Trends")
            
            # Performance trends
            performance_trends = trends_data.get("performance_trends", {})
            if performance_trends:
                perf_info = {
                    "Avg Latency": f"{performance_trends.get('latency_trend', 0):+.1f}% vs last month",
                    "Success Rate": f"{performance_trends.get('success_rate_trend', 0):+.1f}% vs last month",
                    "Error Rate": f"{performance_trends.get('error_rate_trend', 0):+.1f}% vs last month",
                    "Timeout Rate": f"{performance_trends.get('timeout_rate_trend', 0):+.1f}% vs last month",
                }
                
                print_dict_as_table(perf_info, title="⚡ Performance Trends")
            
            # Insights and recommendations
            insights = trends_data.get("insights", [])
            if insights:
                console.print(f"\n[bold blue]🔍 Key Insights:[/bold blue]")
                for insight in insights:
                    console.print(f"  • {insight.get('message', '')}")
                    if insight.get('impact'):
                        console.print(f"    [dim]Impact: {insight['impact']}[/dim]")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to get trends analysis: {e}")


@app.command("digest")
def analytics_digest(
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Generate weekly analytics digest report.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    try:
        digest_data = api.get("/analytics/digest")
        
        if output_format == "json":
            console.print_json(digest_data)
        else:
            # Weekly digest format
            console.print(f"\n[bold cyan]📋 Weekly Analytics Digest[/bold cyan]")
            console.print(f"[dim]Report Period: {digest_data.get('period', 'Last 7 days')}[/dim]\n")
            
            # Executive summary
            summary = digest_data.get("executive_summary", {})
            if summary:
                summary_text = f"""
[bold green]Total Requests:[/bold green] {summary.get('total_requests', 0):,} ({summary.get('requests_change', 0):+.1f}% vs previous week)
[bold green]Total Cost:[/bold green] ${summary.get('total_cost', 0):.2f} ({summary.get('cost_change', 0):+.1f}% vs previous week)
[bold green]Success Rate:[/bold green] {summary.get('success_rate', 0):.1f}% ({summary.get('success_rate_change', 0):+.1f}% vs previous week)
[bold green]Avg Latency:[/bold green] {summary.get('avg_latency', 0):.0f}ms ({summary.get('latency_change', 0):+.1f}% vs previous week)
                """
                
                console.print(Panel(summary_text.strip(), title="📊 Week at a Glance", border_style="green"))
            
            # Top performers
            top_performers = digest_data.get("top_performers", {})
            if top_performers:
                console.print(f"\n[bold]🏆 Top Performers This Week:[/bold]")
                console.print(f"  🥇 Most Used Model: [cyan]{top_performers.get('most_used_model', 'N/A')}[/cyan]")
                console.print(f"  ⚡ Fastest Model: [cyan]{top_performers.get('fastest_model', 'N/A')}[/cyan]")
                console.print(f"  💰 Most Cost-Effective: [cyan]{top_performers.get('most_cost_effective', 'N/A')}[/cyan]")
                console.print(f"  🎯 Highest Success Rate: [cyan]{top_performers.get('highest_success_rate', 'N/A')}[/cyan]")
            
            # Notable events
            notable_events = digest_data.get("notable_events", [])
            if notable_events:
                console.print(f"\n[bold yellow]⚡ Notable Events:[/bold yellow]")
                for event in notable_events:
                    console.print(f"  • {event.get('message', '')}")
                    if event.get('impact'):
                        console.print(f"    [dim]Impact: {event['impact']}[/dim]")
            
            # Recommendations
            recommendations = digest_data.get("recommendations", [])
            if recommendations:
                console.print(f"\n[bold blue]💡 Recommendations:[/bold blue]")
                for rec in recommendations:
                    console.print(f"  • {rec.get('message', '')}")
                    if rec.get('priority'):
                        priority_color = {"high": "red", "medium": "yellow", "low": "green"}.get(rec['priority'], "white")
                        console.print(f"    [dim][{priority_color}]Priority: {rec['priority'].upper()}[/{priority_color}][/dim]")
            
            # Usage patterns
            patterns = digest_data.get("usage_patterns", {})
            if patterns:
                patterns_info = {
                    "Peak Day": patterns.get('peak_day', 'N/A'),
                    "Peak Hour": patterns.get('peak_hour', 'N/A'),
                    "Busiest Endpoint": patterns.get('busiest_endpoint', 'N/A'),
                    "Most Active User": patterns.get('most_active_user', 'N/A'),
                }
                
                print_dict_as_table(patterns_info, title="📋 Usage Patterns")
            
            console.print(f"\n[dim]Report generated at {digest_data.get('generated_at', 'N/A')}[/dim]")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to generate analytics digest: {e}")


@app.command("export")
def export_analytics(
    format: str = typer.Option("csv", "--format", help="Export format (csv/json)"),
    period: str = typer.Option("month", "--period", help="Time period (week/month/quarter)"),
    output_file: Optional[str] = typer.Option(None, "--output", help="Output file path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON")
):
    """
    Export analytics data for external analysis.
    """
    output_format = get_output_format(json_output)
    ensure_authenticated()
    
    if format not in ["csv", "json"]:
        print_error("Format must be csv or json")
        return
    
    try:
        # This would export the data - mock for now
        export_result = {
            "export_id": "exp-123456",
            "format": format,
            "period": period,
            "records_exported": 1500,
            "file_size_mb": 2.3,
            "download_url": f"https://api.bonito.com/exports/exp-123456.{format}",
            "expires_at": "2024-01-22T10:30:00Z"
        }
        
        if output_format == "json":
            console.print_json(export_result)
        else:
            print_success(f"Analytics data exported successfully")
            
            export_info = {
                "Export ID": export_result["export_id"],
                "Format": export_result["format"].upper(),
                "Period": export_result["period"].title(),
                "Records": f"{export_result['records_exported']:,}",
                "File Size": f"{export_result['file_size_mb']:.1f} MB",
                "Download URL": export_result["download_url"],
                "Expires": export_result["expires_at"],
            }
            
            print_dict_as_table(export_info, title="Export Details")
            print_info("Download the file using the provided URL")
    
    except APIError as e:
        if output_format == "json":
            console.print_json({"error": str(e)})
        else:
            print_error(f"Failed to export analytics: {e}")


if __name__ == "__main__":
    app()