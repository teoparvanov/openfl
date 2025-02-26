import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.subplots as sp
from datetime import datetime
from dateutil.relativedelta import relativedelta
from tqdm import tqdm
import argparse
import os
from PIL import Image

OPENFL_GITHUB_API_URL = "https://api.github.com/repos/securefederatedai/openfl"
OPENFL_CONTRIB_GITHUB_API_URL = "https://api.github.com/repos/securefederatedai/openfl-contrib"

KNOWN_EXTERNAL_CONTRIBUTORS = {
    "refai06",
    "ishant162",
    "scngupta-dsp",
    "changhongyan123"
}

def fetch_github_data():
    api_token = os.getenv("GITHUB_API_TOKEN")
    if not api_token:
        raise ValueError("GITHUB_API_TOKEN environment variable not set")
    headers = {"Authorization": f"token {api_token}"}
    # Fetch repository data
    repo_data = requests.get(OPENFL_GITHUB_API_URL, headers=headers).json()

    # Fetch issues data
    issues_data = requests.get(f"{OPENFL_GITHUB_API_URL}/issues", headers=headers, params={"state": "all"}).json()

    # Fetch pull requests data
    pulls_data = requests.get(f"{OPENFL_GITHUB_API_URL}/pulls", headers=headers, params={"state": "all"}).json()

    # Fetch contributors data
    contributors_data = requests.get(f"{OPENFL_GITHUB_API_URL}/contributors", headers=headers).json()

    return repo_data, issues_data, pulls_data, contributors_data

def fetch_forks_data():
    api_token = os.getenv("GITHUB_API_TOKEN")
    if not api_token:
        raise ValueError("GITHUB_API_TOKEN environment variable not set")
    headers = {"Authorization": f"token {api_token}"}
    # Fetch forks data with progress bar
    forks_data = []
    page = 1
    with tqdm(desc="Fetching OpenFL forks", unit="page") as pbar:
        while True:
            response = requests.get(f"{OPENFL_GITHUB_API_URL}/forks", headers=headers, params={"page": page, "per_page": 100}).json()
            if not response:
                break
            forks_data.extend(response)
            page += 1
            pbar.update(1)
    return forks_data

def fetch_stars_data():
    api_token = os.getenv("GITHUB_API_TOKEN")
    if not api_token:
        raise ValueError("GITHUB_API_TOKEN environment variable not set")
    headers = {"Authorization": f"token {api_token}"}
    headers["Accept"] = "application/vnd.github.star+json"
    # Fetch stars data with progress bar
    stars_data = []
    page = 1
    with tqdm(desc="Fetching OpenFL stars", unit="page") as pbar:
        while True:
            response = requests.get(f"{OPENFL_GITHUB_API_URL}/stargazers", headers=headers, params={"page": page, "per_page": 100}).json()
            if not response:
                break
            stars_data.extend(response)
            page += 1
            pbar.update(1)
    return stars_data

def fetch_quarter_dates(year, month):
    quarter = (month - 1) // 3 + 1
    start_month = 3 * (quarter - 1) + 1
    end_month = start_month + 2
    start_date = datetime(year, start_month, 1)
    end_date = start_date + relativedelta(months=3)
    return start_date, end_date

def fetch_monthly_data(year, month):
    api_token = os.getenv("GITHUB_API_TOKEN")
    if not api_token:
        raise ValueError("GITHUB_API_TOKEN environment variable not set")
    headers = {"Authorization": f"token {api_token}"}
    # Calculate the start and end of the given month
    start_date = datetime(year, month, 1)
    end_date = start_date + relativedelta(months=1)

    # Format the start and end of the month
    month_start = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    month_end = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Calculate the start and end of the quarter
    quarter_start_date, quarter_end_date = fetch_quarter_dates(year, month)
    quarter_start = quarter_start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    quarter_end = quarter_end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Initialize metrics
    monthly_pulls = 0
    monthly_contributors = set()
    monthly_contributors_non_intel = set()

    # Initialize metrics for issues
    total_issue_close_time = 0
    closed_issues_count = 0

    # Initialize metrics for response times
    total_pr_response_time = 0
    pr_response_count = 0
    total_discussion_response_time = 0
    discussion_response_count = 0

    # Fetch pull requests merged in the month with optimized filtering
    page = 1
    with tqdm(desc="Fetching OpenFL merged PRs", unit="page") as pbar:
        while True:
            pulls = requests.get(
                f"{OPENFL_GITHUB_API_URL}/pulls",
                headers=headers,
                params={
                    "state": "closed",
                    "sort": "updated",
                    "direction": "desc",
                    "page": page,
                    "per_page": 100,
                    "since": month_start,
                    "until": month_end
                }
            ).json()
            if not pulls:
                break
            for pull in pulls:
                if 'merged_at' in pull and pull['merged_at'] and month_start <= pull['merged_at'] < month_end:
                    monthly_pulls += 1
                    if 'user' in pull and pull['user']:
                        contributor = pull['user']['login']
                        monthly_contributors.add(contributor)
                        if contributor in KNOWN_EXTERNAL_CONTRIBUTORS:
                            monthly_contributors_non_intel.add(contributor)
                    if 'created_at' in pull and 'closed_at' in pull:
                        created_at = datetime.strptime(pull['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                        closed_at = datetime.strptime(pull['closed_at'], '%Y-%m-%dT%H:%M:%SZ')
                        total_pr_response_time += (closed_at - created_at).total_seconds()
                        pr_response_count += 1
            page += 1
            pbar.update(1)

    # Fetch issues created and closed in the quarter with optimized filtering
    page = 1
    with tqdm(desc="Fetching OpenFL closed issues", unit="page") as pbar:
        while True:
            issues = requests.get(
                f"{OPENFL_GITHUB_API_URL}/issues",
                headers=headers,
                params={
                    "state": "closed",
                    "sort": "updated",
                    "direction": "desc",
                    "page": page,
                    "per_page": 100,
                    "since": quarter_start,
                    "until": quarter_end
                }
            ).json()
            if not issues:
                break
            for issue in issues:
                if 'closed_at' in issue and issue['closed_at'] and quarter_start <= issue['closed_at'] < quarter_end:
                    created_at = datetime.strptime(issue['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    closed_at = datetime.strptime(issue['closed_at'], '%Y-%m-%dT%H:%M:%SZ')
                    if quarter_start <= issue['created_at'] < quarter_end:
                        closed_issues_count += 1
                        total_issue_close_time += (closed_at - created_at).total_seconds()
            page += 1
            pbar.update(1)

    # Fetch discussions created in the quarter and measure time to first comment
    page = 1
    with tqdm(desc="Fetching OpenFL discussions", unit="page") as pbar:
        while True:
            discussions = requests.get(
                f"{OPENFL_GITHUB_API_URL}/discussions",
                headers=headers,
                params={
                    "state": "all",
                    "sort": "created",
                    "direction": "desc",
                    "page": page,
                    "per_page": 100,
                    "since": quarter_start,
                    "until": quarter_end
                }
            ).json()
            if not discussions:
                break
            for discussion in discussions:
                if 'created_at' in discussion:
                    created_at = datetime.strptime(discussion['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    if 'comments' in discussion and discussion['comments'] > 0:
                        discussion_number = discussion['number']
                        comments_url = f"{OPENFL_GITHUB_API_URL}/discussions/{discussion_number}/comments"
                        first_comment = requests.get(comments_url, headers=headers).json()[0]
                        first_comment_at = datetime.strptime(first_comment['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                        total_discussion_response_time += (first_comment_at - created_at).total_seconds()
                        discussion_response_count += 1
            page += 1
            pbar.update(1)

    # Calculate average response times in days
    avg_pr_response_time = (total_pr_response_time / pr_response_count) / 86400 if pr_response_count > 0 else 0
    avg_discussion_response_time = (total_discussion_response_time / discussion_response_count) / 86400 if discussion_response_count > 0 else 0

    # Calculate average issue close time in days
    avg_issue_close_time = (total_issue_close_time / closed_issues_count) / 86400 if closed_issues_count > 0 else 0

    # Fetch forks data
    forks_data = fetch_forks_data()

    # Filter forks data up to the specified month
    forks_count = []
    for fork in forks_data:
        created_at = datetime.strptime(fork['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        if created_at <= end_date:
            forks_count.append(created_at)

    # Sort forks by creation date
    forks_count.sort()

    # Fetch stars data
    stars_data = fetch_stars_data()

    # Filter stars data up to the specified month
    stars_count = []
    for star in stars_data:
        starred_at = datetime.strptime(star['starred_at'], '%Y-%m-%dT%H:%M:%SZ')
        if starred_at <= end_date:
            stars_count.append(starred_at)

    # Sort stars by creation date
    stars_count.sort()

    return monthly_pulls, len(monthly_contributors), len(monthly_contributors_non_intel), avg_issue_close_time, forks_count, avg_pr_response_time, avg_discussion_response_time, stars_count

def create_mock_data():
    # Generate mock data
    monthly_pulls = 50
    monthly_contributors = 20
    non_intel_contributors = 10
    avg_issue_close_time = 5
    forks_count = [datetime(2025, 1, i) for i in range(1, 31)]
    avg_pr_response_time = 2
    avg_discussion_response_time = 1
    stars_count = [datetime(2025, 1, i) for i in range(1, 31)]

    return monthly_pulls, monthly_contributors, non_intel_contributors, avg_issue_close_time, forks_count, avg_pr_response_time, avg_discussion_response_time, stars_count

def create_github_metrics_figure(monthly_pulls, monthly_contributors, non_intel_contributors, avg_issue_close_time, forks_count, avg_pr_response_time, avg_discussion_response_time, stars_count):
    # Create GitHub repository metrics gauges
    pr_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=monthly_pulls,
        gauge={'axis': {'range': [0, 100]}},
        title={'text': "Merged Pull Requests"}
    ))

    contributors_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=monthly_contributors,
        gauge={'axis': {'range': [0, 100]}},
        title={'text': "Code Contributors (All)"}
    ))

    non_intel_contributors_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=non_intel_contributors,
        gauge={'axis': {'range': [0, 100]}},
        title={'text': "Code Contributors (Non-Intel)"}
    ))

    issue_close_time_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_issue_close_time,
        gauge={'axis': {'range': [0, 30]}},
        title={'text': "Average Issue Close Time (Days)"}
    ))

    pr_response_time_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_pr_response_time,
        gauge={'axis': {'range': [0, 30]}},
        title={'text': "Average PR Response Time (Days)"}
    ))

    discussion_response_time_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avg_discussion_response_time,
        gauge={'axis': {'range': [0, 30]}},
        title={'text': "Average Discussion Response Time (Days)"}
    ))

    # Create a line chart for forks
    forks_df = pd.DataFrame(forks_count, columns=['created_at'])
    forks_df['count'] = range(1, len(forks_df) + 1)
    forks_line_chart = px.line(forks_df, x='created_at', y='count', title='Number of Forks Over Time')

    # Create a line chart for stars
    stars_df = pd.DataFrame(stars_count, columns=['starred_at'])
    stars_df['count'] = range(1, len(stars_df) + 1)
    stars_line_chart = px.line(stars_df, x='starred_at', y='count', title='Number of Stars Over Time')

    # Combine the GitHub metrics into a single figure
    github_fig = sp.make_subplots(
        rows=4, cols=2, 
        specs=[[{"type": "xy"}, {"type": "xy"}], [{"type": "indicator"}, {"type": "indicator"}], [{"type": "indicator"}, {"type": "indicator"}], [{"type": "indicator"}, {"type": "indicator"}]],
        vertical_spacing=0.1
    )
    for trace in stars_line_chart.data:
        github_fig.add_trace(trace, row=1, col=1)
    for trace in forks_line_chart.data:
        github_fig.add_trace(trace, row=1, col=2)
    for trace in pr_gauge.data:
        github_fig.add_trace(trace, row=2, col=1)
    for trace in contributors_gauge.data:
        github_fig.add_trace(trace, row=2, col=2)
    for trace in issue_close_time_gauge.data:
        github_fig.add_trace(trace, row=3, col=1)
    for trace in non_intel_contributors_gauge.data:
        github_fig.add_trace(trace, row=3, col=2)
    for trace in pr_response_time_gauge.data:
        github_fig.add_trace(trace, row=4, col=1)
    for trace in discussion_response_time_gauge.data:
        github_fig.add_trace(trace, row=4, col=2)

    github_fig.update_layout(
        height=1000,
        title={
            'text': "OpenFL GitHub Metrics",
            'y': 0.98,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 24}
        },
        showlegend=False
    )

    return github_fig

def create_social_media_metrics_figure():
    # Create mock social media metrics gauges
    linkedin_followers_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=4,  # Mock value
        gauge={'axis': {'range': [0, 50]}},
        title={'text': "LinkedIn #OpenFL mentions"}
    ))
        
    x_followers_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=1,  # Mock value
        gauge={'axis': {'range': [0, 50]}},
        title={'text': "X #OpenFL mentions"}
    ))

    community_meeting_attendees_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=18,  # Mock value
        gauge={'axis': {'range': [0, 100]}},
        title={'text': "Community Meeting Attendees"}
    ))

    # Combine the social media metrics into a single figure
    social_media_fig = sp.make_subplots(
        rows=1, cols=3,
        specs=[[{"type": "indicator"}, {"type": "indicator"}, {"type": "indicator"}]],
        vertical_spacing=0.1
    )

    for trace in linkedin_followers_gauge.data:
        social_media_fig.add_trace(trace, row=1, col=1)
    for trace in community_meeting_attendees_gauge.data:
        social_media_fig.add_trace(trace, row=1, col=2)
    for trace in x_followers_gauge.data:
        social_media_fig.add_trace(trace, row=1, col=3)


    social_media_fig.update_layout(
        height=400,
        title={
            'text': "Social Media Metrics",
            'y': 0.98,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 24}
        },
        showlegend=False
    )

    return social_media_fig

def create_key_partners_figure():
    # Load all logos from the ./partner-logos folder
    logos = []
    logos_path = "./partner-logos"
    for filename in os.listdir(logos_path):
        if filename.endswith(".png") or filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".jfif"):
            img = Image.open(os.path.join(logos_path, filename))
            logos.append(img)

    # Create a figure to display the logos
    fig = go.Figure()
    for i, logo in enumerate(logos):
        fig.add_layout_image(
            dict(
                source=logo,
                xref="x",
                yref="y",
                x=i * 2,  # Adjust x position to accommodate larger size
                y=1,
                sizex=2,  # Double the size
                sizey=2,  # Double the size
                xanchor="center",
                yanchor="middle"
            )
        )

    fig.update_layout(
        title={
            'text': "Key Partners",
            'y': 0.98,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 24}
        },
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
        height=400,  # Adjust height to accommodate larger logos
        margin=dict(l=0, r=0, t=40, b=0)
    )

    return fig

def fetch_pypi_downloads():
    # Placeholder for actual retrieval of PyPi download data
    return 359  # Mock value

def fetch_docker_downloads():
    # Placeholder for actual retrieval of Docker download data
    return 8  # Mock value

def create_openfl_binaries_figure(pypi_downloads, docker_downloads):
    # Create gauges for PyPi and Docker downloads
    pypi_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pypi_downloads,
        gauge={'axis': {'range': [0, 5000]}},
        title={'text': "Monthly PyPi downloads"}
    ))

    docker_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=docker_downloads,
        gauge={'axis': {'range': [0, 5000]}},
        title={'text': "Monthly docker downloads"}
    ))

    # Combine the gauges into a single figure
    binaries_fig = sp.make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}]],
        vertical_spacing=0.1
    )
    for trace in pypi_gauge.data:
        binaries_fig.add_trace(trace, row=1, col=1)
    for trace in docker_gauge.data:
        binaries_fig.add_trace(trace, row=1, col=2)

    binaries_fig.update_layout(
        height=400,
        title={
            'text': "OpenFL Binaries (latest stable)",
            'y': 0.98,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 24}
        },
        showlegend=False
    )

    return binaries_fig

def fetch_openfl_contrib_data(year, month):
    api_token = os.getenv("GITHUB_API_TOKEN")
    if not api_token:
        raise ValueError("GITHUB_API_TOKEN environment variable not set")
    headers = {"Authorization": f"token {api_token}"}
    # Calculate the start and end of the given month
    start_date = datetime(year, month, 1)
    end_date = start_date + relativedelta(months=1)

    # Format the start and end of the month
    month_start = start_date.strftime('%Y-%m-%dT%H:%M:%SZ')
    month_end = end_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Fetch pull requests data for the selected month
    pulls_data = []
    contributors_set = set()
    page = 1
    with tqdm(desc="Fetching openfl-contrib PRs", unit="page") as pbar:
        while True:
            response = requests.get(
                f"{OPENFL_CONTRIB_GITHUB_API_URL}/pulls",
                headers=headers,
                params={
                    "state": "closed",
                    "sort": "updated",
                    "direction": "desc",
                    "page": page,
                    "per_page": 100,
                    "since": month_start,
                    "until": month_end
                }
            ).json()
            if not response:
                break
            for pull in response:
                if 'merged_at' in pull and pull['merged_at'] and month_start <= pull['merged_at'] < month_end:
                    pulls_data.append(pull)
                    if 'user' in pull and pull['user']:
                        contributors_set.add(pull['user']['login'])
            page += 1
            pbar.update(1)

    return pulls_data, contributors_set

def create_openfl_contrib_figure(year, month, use_mock=False):
    if use_mock:
        # Use mock data
        pr_count = 75  # Mock value
        contributors_count = 50  # Mock value
    else:
        # Fetch data from openfl-contrib repository
        pulls_data, contributors_set = fetch_openfl_contrib_data(year, month)
        pr_count = len(pulls_data)
        contributors_count = len(contributors_set)

    # Create gauges for Merged Pull Requests and Code Contributors
    pr_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=pr_count,
        gauge={'axis': {'range': [0, 100]}},
        title={'text': "Merged Pull Requests"}
    ))

    contributors_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=contributors_count,
        gauge={'axis': {'range': [0, 100]}},
        title={'text': "Code Contributors"}
    ))

    # Combine the gauges into a single figure
    contrib_fig = sp.make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "indicator"}, {"type": "indicator"}]],
        vertical_spacing=0.1
    )
    for trace in pr_gauge.data:
        contrib_fig.add_trace(trace, row=1, col=1)
    for trace in contributors_gauge.data:
        contrib_fig.add_trace(trace, row=1, col=2)

    contrib_fig.update_layout(
        height=400,
        title={
            'text': "OpenFL-Contrib GitHub Metrics",
            'y': 0.98,
            'x': 0.5,
            'xanchor': 'center',
            'yanchor': 'top',
            'font': {'size': 24}
        },
        showlegend=False
    )

    return contrib_fig

def create_dashboard(year, month, use_mock=False):
    if use_mock:
        # Use mock data
        monthly_pulls, monthly_contributors, non_intel_contributors, avg_issue_close_time, forks_count, avg_pr_response_time, avg_discussion_response_time, stars_count = create_mock_data()
        pypi_downloads = 1000  # Mock value
        docker_downloads = 500  # Mock value
    else:
        # Fetch monthly data
        monthly_pulls, monthly_contributors, non_intel_contributors, avg_issue_close_time, forks_count, avg_pr_response_time, avg_discussion_response_time, stars_count = fetch_monthly_data(year, month)
        pypi_downloads = fetch_pypi_downloads()
        docker_downloads = fetch_docker_downloads()

    # Create figures for GitHub and social media metrics
    key_partners_fig = create_key_partners_figure()
    binaries_fig = create_openfl_binaries_figure(pypi_downloads, docker_downloads)
    github_fig = create_github_metrics_figure(monthly_pulls, monthly_contributors, non_intel_contributors, avg_issue_close_time, forks_count, avg_pr_response_time, avg_discussion_response_time, stars_count)
    social_media_fig = create_social_media_metrics_figure()
    contrib_fig = create_openfl_contrib_figure(year, month, use_mock)

    # Get the month name
    month_name = datetime(year, month, 1).strftime('%B')

    # Combine all figures into a single HTML file with a title
    with open("/mnt/c/Users/tparvano/Downloads/openfl_engagement_dashboard.html", "w") as f:
        f.write(f"<h1 style='text-align:center;'>OpenFL Community Engagement Metrics for {month_name} {year}</h1>")
        if use_mock:
            f.write("<h2 style='text-align:center; background-color: yellow;'>(RENDERED WITH MOCK DATA)</h2>")
        f.write(key_partners_fig.to_html(full_html=False, include_plotlyjs='cdn'))
        f.write(binaries_fig.to_html(full_html=False, include_plotlyjs=False))
        f.write(github_fig.to_html(full_html=False, include_plotlyjs=False))
        f.write(contrib_fig.to_html(full_html=False, include_plotlyjs=False))
        f.write(social_media_fig.to_html(full_html=False, include_plotlyjs=False))
        f.write("</body></html>")
    
    print("Combined plot saved as openfl_engagement_dashboard.html. Open this file in a web browser to view the plot.")

def main():
    parser = argparse.ArgumentParser(description="Generate OpenFL Engagement Metrics Dashboard")
    parser.add_argument("--year", type=int, required=True, help="Year for the dashboard")
    parser.add_argument("--month", type=int, required=True, help="Month for the dashboard")
    parser.add_argument("--mock", action="store_true", help="Use mock data instead of fetching from APIs")
    args = parser.parse_args()

    create_dashboard(year=args.year, month=args.month, use_mock=args.mock)

if __name__ == "__main__":
    main()
