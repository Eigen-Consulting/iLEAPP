"""
Dashboard Generator for iLEAPP

This module generates the "At a Glance Dashboard" that appears at the top of iLEAPP reports.
It creates HTML widgets showing aggregated statistics from various artifacts.
"""

import json
from scripts.aggregation_engine import AggregationEngine


def generate_dashboard_html(report_folder: str) -> str:
    """
    Generate the complete dashboard HTML section.
    
    Args:
        report_folder: Path to the report folder
        
    Returns:
        Complete HTML string for the dashboard section
    """
    dashboard_data = AggregationEngine.get_dashboard_data()
    
    if not AggregationEngine.has_data():
        return ""  # No dashboard if no data collected
    
    # Generate individual components
    try:
        summary_cards = generate_summary_cards(dashboard_data['summary'])
        messaging_widget = generate_messaging_widget(dashboard_data['messaging_apps'])
        device_widget = generate_device_info_widget(dashboard_data['device_info'])
        additional_widgets = generate_additional_widgets(dashboard_data)
        
        # Build the main dashboard HTML
        dashboard_html = f"""
    <div class="container-fluid mt-4">
        <div class="row">
            <div class="col-12">
                <div class="card shadow-sm">
                    <div class="card-header bg-primary text-white">
                        <h4 class="mb-0">
                            <i data-feather="bar-chart-2" class="mr-2"></i>
                            At a Glance Dashboard
                        </h4>
                        <small>Aggregated statistics from all processed artifacts</small>
                    </div>
                    <div class="card-body">
                        <div class="row">
                            {summary_cards}
                        </div>
                        <div class="row mt-4">
                            {messaging_widget}
                            {device_widget}
                        </div>
                        {additional_widgets}
                    </div>
                </div>
            </div>
        </div>
    </div>
    """
        
        return dashboard_html
    except Exception as e:
        # If there's any error, return empty string
        return ""


def generate_summary_cards(summary_data: dict) -> str:
    """Generate summary statistic cards."""
    cards = []
    
    card_configs = [
        {
            'title': 'Total Messages',
            'value': summary_data.get('total_messages', 0),
            'icon': 'message-circle',
            'color': 'primary'
        },
        {
            'title': 'Artifacts Processed',
            'value': summary_data.get('total_artifacts_processed', 0),
            'icon': 'layers',
            'color': 'success'
        },
        {
            'title': 'Location Points',
            'value': summary_data.get('total_location_points', 0),
            'icon': 'map-pin',
            'color': 'info'
        },
        {
            'title': 'Processing Errors',
            'value': summary_data.get('processing_errors', 0),
            'icon': 'alert-triangle',
            'color': 'warning' if summary_data.get('processing_errors', 0) > 0 else 'success'
        }
    ]
    
    for config in card_configs:
        card_html = f"""
        <div class="col-md-3 col-sm-6 mb-3">
            <div class="card border-{config['color']} h-100">
                <div class="card-body text-center">
                    <i data-feather="{config['icon']}" class="text-{config['color']} mb-2" style="width: 2rem; height: 2rem;"></i>
                    <h3 class="text-{config['color']}">{config['value']:,}</h3>
                    <p class="card-text text-muted">{config['title']}</p>
                </div>
            </div>
        </div>
        """
        cards.append(card_html)
    
    return ''.join(cards)


def generate_messaging_widget(messaging_data: dict) -> str:
    """Generate the top messaging apps widget."""
    if not messaging_data.get('apps'):
        return """
        <div class="col-md-8">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Top Messaging Apps</h5>
                </div>
                <div class="card-body">
                    <p class="text-muted">No messaging data found.</p>
                </div>
            </div>
        </div>
        """
    
    # Sort apps by message count
    top_apps = messaging_data['apps'][:10]  # Top 10 apps
    chart_data = AggregationEngine.get_messaging_chart_data()
    
    # Generate chart HTML
    chart_html = generate_messaging_chart(chart_data)
    
    # Generate table rows
    table_rows = []
    for i, (app_name, message_count) in enumerate(top_apps, 1):
        percentage = (message_count / messaging_data['total'] * 100) if messaging_data['total'] > 0 else 0
        
        row_html = f"""
        <tr>
            <td><strong>{i}</strong></td>
            <td>{app_name}</td>
            <td class="text-right">
                <span class="badge badge-primary">{message_count:,}</span>
            </td>
            <td class="text-right">{percentage:.1f}%</td>
        </tr>
        """
        table_rows.append(row_html)
    
    return f"""
    <div class="col-md-8">
        <div class="card">
            <div class="card-header d-flex justify-content-between align-items-center">
                <h5 class="mb-0">
                    <i data-feather="message-square" class="mr-2"></i>
                    Top Messaging Apps
                </h5>
                <small class="text-muted">Total: {messaging_data['total']:,} messages</small>
            </div>
            <div class="card-body">
                <div class="row">
                    <div class="col-md-7">
                        {chart_html}
                    </div>
                    <div class="col-md-5">
                        <div class="table-responsive">
                            <table class="table table-sm">
                                <thead>
                                    <tr>
                                        <th>#</th>
                                        <th>App</th>
                                        <th class="text-right">Messages</th>
                                        <th class="text-right">%</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {''.join(table_rows)}
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
    """


def generate_messaging_chart(chart_data: dict) -> str:
    """Generate Chart.js bar chart for messaging apps."""
    if not chart_data.get('labels'):
        return '<p class="text-muted">No data available for chart.</p>'
    
    # Prepare data for Chart.js
    labels_json = json.dumps(chart_data['labels'])
    data_json = json.dumps(chart_data['data'])
    
    # Generate colors for bars
    colors = [
        '#007bff', '#28a745', '#ffc107', '#dc3545', '#6f42c1',
        '#fd7e14', '#e83e8c', '#20c997', '#6c757d', '#343a40'
    ]
    
    background_colors = json.dumps(colors[:len(chart_data['labels'])])
    
    return f"""
    <div style="position: relative; height: 300px;">
        <canvas id="messagingChart"></canvas>
    </div>
    <script>
    document.addEventListener('DOMContentLoaded', function() {{
        var ctx = document.getElementById('messagingChart').getContext('2d');
        var chart = new Chart(ctx, {{
            type: 'bar',
            data: {{
                labels: {labels_json},
                datasets: [{{
                    label: 'Messages',
                    data: {data_json},
                    backgroundColor: {background_colors},
                    borderColor: {background_colors},
                    borderWidth: 1
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{
                            callback: function(value) {{
                                return value.toLocaleString();
                            }}
                        }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        display: false
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                return context.parsed.y.toLocaleString() + ' messages';
                            }}
                        }}
                    }}
                }}
            }}
        }});
    }});
    </script>
    """


def generate_device_info_widget(device_info: dict) -> str:
    """Generate device information widget."""
    if not device_info:
        return """
        <div class="col-md-4">
            <div class="card">
                <div class="card-header">
                    <h5 class="mb-0">Device Information</h5>
                </div>
                <div class="card-body">
                    <p class="text-muted">No device information available.</p>
                </div>
            </div>
        </div>
        """
    
    info_rows = []
    for key, value in device_info.items():
        formatted_key = key.replace('_', ' ').title()
        info_rows.append(f"""
        <tr>
            <td><strong>{formatted_key}</strong></td>
            <td>{value}</td>
        </tr>
        """)
    
    return f"""
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i data-feather="smartphone" class="mr-2"></i>
                    Device Information
                </h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-sm table-borderless">
                        <tbody>
                            {''.join(info_rows)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    """


def generate_additional_widgets(dashboard_data: dict) -> str:
    """Generate additional widgets based on available data."""
    widgets = []
    
    # Social media widget
    if dashboard_data.get('social_media_apps', {}).get('apps'):
        widgets.append(generate_social_media_widget(dashboard_data['social_media_apps']))
    
    # Location sources widget
    if dashboard_data.get('location_sources', {}).get('sources'):
        widgets.append(generate_location_widget(dashboard_data['location_sources']))
    
    # Processing errors widget
    if dashboard_data.get('errors'):
        widgets.append(generate_errors_widget(dashboard_data['errors']))
    
    if widgets:
        return f'<div class="row mt-4">{"".join(widgets)}</div>'
    
    return ""


def generate_social_media_widget(social_data: dict) -> str:
    """Generate social media apps widget."""
    top_apps = social_data['apps'][:5]
    
    app_rows = []
    for app_name, activity_count in top_apps:
        app_rows.append(f"""
        <tr>
            <td>{app_name}</td>
            <td class="text-right">{activity_count:,}</td>
        </tr>
        """)
    
    return f"""
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i data-feather="users" class="mr-2"></i>
                    Social Media Activity
                </h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>App</th>
                                <th class="text-right">Activities</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(app_rows)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    """


def generate_location_widget(location_data: dict) -> str:
    """Generate location sources widget."""
    top_sources = location_data['sources'][:5]
    
    source_rows = []
    for source_name, location_count in top_sources:
        source_rows.append(f"""
        <tr>
            <td>{source_name}</td>
            <td class="text-right">{location_count:,}</td>
        </tr>
        """)
    
    return f"""
    <div class="col-md-4">
        <div class="card">
            <div class="card-header">
                <h5 class="mb-0">
                    <i data-feather="map-pin" class="mr-2"></i>
                    Location Data Sources
                </h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Source</th>
                                <th class="text-right">Points</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(source_rows)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    </div>
    """


def generate_errors_widget(errors_data: list) -> str:
    """Generate processing errors widget."""
    if not errors_data:
        return ""
    
    error_rows = []
    for error in errors_data[:10]:  # Show max 10 errors
        error_rows.append(f"""
        <tr>
            <td>{error.get('artifact', 'Unknown')}</td>
            <td><small class="text-muted">{error.get('error', 'No details')}</small></td>
        </tr>
        """)
    
    return f"""
    <div class="col-md-8">
        <div class="card border-warning">
            <div class="card-header bg-warning text-dark">
                <h5 class="mb-0">
                    <i data-feather="alert-triangle" class="mr-2"></i>
                    Processing Errors ({len(errors_data)})
                </h5>
            </div>
            <div class="card-body">
                <div class="table-responsive">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Artifact</th>
                                <th>Error Details</th>
                            </tr>
                        </thead>
                        <tbody>
                            {''.join(error_rows)}
                        </tbody>
                    </table>
                </div>
                {f'<small class="text-muted">Showing first 10 of {len(errors_data)} errors.</small>' if len(errors_data) > 10 else ''}
            </div>
        </div>
    </div>
    """


def get_chart_js_script() -> str:
    """Return the Chart.js script tag for charts."""
    return '<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>'