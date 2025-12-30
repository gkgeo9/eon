"""
Example usage of the LeadershipExtractor for custom SEC filing analysis.

This script demonstrates how to:
1. Extract leadership teams from 14A proxy statements
2. Get detailed profiles for individual leaders
3. Analyze overall leadership quality
4. Custom scripting for specific use cases
"""

import json
import logging
from pathlib import Path

from experimentation.leadership_extractor import LeadershipExtractor, extract_leadership
from experimentation.schemas import LeadershipMember, LeaderDetailedProfile


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def example_1_basic_extraction():
    """Example 1: Basic leadership team extraction."""
    print("\n" + "="*80)
    print("EXAMPLE 1: Basic Leadership Team Extraction")
    print("="*80 + "\n")

    ticker = "AAPL"

    # Simple one-liner
    data = extract_leadership(ticker, detailed=False)
    team = data['team']

    print(f"Company: {team.company_name} ({team.ticker})")
    print(f"Fiscal Year: {team.fiscal_year}")
    print(f"\nBoard of Directors: {len(team.board_of_directors)} members")
    print(f"Executive Officers: {len(team.executive_officers)} members")

    print("\n--- Board Members ---")
    for director in team.board_of_directors[:3]:  # Show first 3
        print(f"  • {director.name} - {director.title}")
        if director.independence_status:
            print(f"    Independence: {director.independence_status}")

    print("\n--- Top Executives ---")
    for exec in team.executive_officers[:3]:  # Show first 3
        print(f"  • {exec.name} - {exec.title}")
        if exec.total_compensation:
            print(f"    Total Comp: ${exec.total_compensation:,.0f}")


def example_2_detailed_profiles():
    """Example 2: Extract detailed profiles for each leader."""
    print("\n" + "="*80)
    print("EXAMPLE 2: Detailed Leadership Profiles")
    print("="*80 + "\n")

    ticker = "MSFT"

    extractor = LeadershipExtractor()

    # Extract team first
    team = extractor.extract_leadership_team(ticker)

    # Get detailed profile for CEO only
    ceo = team.executive_officers[0]  # Typically the CEO is first
    print(f"Researching: {ceo.name} ({ceo.title})")

    profile = extractor.extract_detailed_profile(
        leader=ceo,
        ticker=ticker
        # Google Search is automatically enabled in LeadershipExtractor
    )

    print(f"\n--- Detailed Profile: {profile.name} ---")
    print(f"Current Role: {profile.current_title} at {profile.current_company}")

    if profile.career_history:
        print(f"\nCareer History:")
        for position in profile.career_history[:5]:
            print(f"  • {position}")

    if profile.education_details:
        print(f"\nEducation:")
        for edu in profile.education_details:
            print(f"  • {edu}")

    if profile.notable_achievements:
        print(f"\nNotable Achievements:")
        for achievement in profile.notable_achievements[:3]:
            print(f"  • {achievement}")

    if profile.leadership_style:
        print(f"\nLeadership Style:")
        print(f"  {profile.leadership_style}")


def example_3_full_analysis():
    """Example 3: Complete leadership analysis with quality assessment."""
    print("\n" + "="*80)
    print("EXAMPLE 3: Full Leadership Quality Analysis")
    print("="*80 + "\n")

    ticker = "NVDA"

    # Get everything in one call
    data = extract_leadership(ticker, detailed=True)

    team = data['team']
    profiles = data['profiles']
    analysis = data['analysis']

    print(f"Company: {team.company_name} ({ticker})")
    print(f"Total Leadership Analyzed: {len(profiles)} people\n")

    print("--- Leadership Analysis ---")
    print(json.dumps(analysis, indent=2))


def example_4_custom_research():
    """Example 4: Custom research on specific leaders."""
    print("\n" + "="*80)
    print("EXAMPLE 4: Custom Research Script")
    print("="*80 + "\n")

    ticker = "TSLA"

    extractor = LeadershipExtractor()

    # Extract team
    team = extractor.extract_leadership_team(ticker)

    # Custom: Find all directors who serve on other boards
    multi_board_directors = []

    for director in team.board_of_directors:
        if director.other_boards and len(director.other_boards) > 0:
            multi_board_directors.append(director)

    print(f"Directors serving on multiple boards: {len(multi_board_directors)}")
    for director in multi_board_directors:
        print(f"\n{director.name} - {director.title}")
        print(f"  Other Boards: {', '.join(director.other_boards)}")

    # Custom: Analyze executive compensation spread
    execs_with_comp = [e for e in team.executive_officers if e.total_compensation]
    if execs_with_comp:
        execs_with_comp.sort(key=lambda x: x.total_compensation, reverse=True)

        print(f"\n--- Executive Compensation Ranking ---")
        for i, exec in enumerate(execs_with_comp, 1):
            print(f"{i}. {exec.name}: ${exec.total_compensation:,.0f}")

        if len(execs_with_comp) > 1:
            ceo_comp = execs_with_comp[0].total_compensation
            median_comp = execs_with_comp[len(execs_with_comp)//2].total_compensation
            ratio = ceo_comp / median_comp if median_comp > 0 else 0

            print(f"\nCEO to Median Executive Pay Ratio: {ratio:.2f}x")


def example_5_batch_comparison():
    """Example 5: Compare leadership across multiple companies."""
    print("\n" + "="*80)
    print("EXAMPLE 5: Multi-Company Leadership Comparison")
    print("="*80 + "\n")

    tickers = ["AAPL", "MSFT", "GOOGL"]

    extractor = LeadershipExtractor()
    comparison = {}

    for ticker in tickers:
        print(f"Analyzing {ticker}...")
        try:
            team = extractor.extract_leadership_team(ticker, save_to_file=True)

            comparison[ticker] = {
                "company": team.company_name,
                "total_directors": team.total_directors,
                "total_executives": team.total_executives,
                "independent_directors": team.independent_directors_count,
                "avg_tenure": team.average_director_tenure,
                "board_diversity": team.board_diversity_summary
            }

        except Exception as e:
            logger.error(f"Failed to analyze {ticker}: {e}")
            continue

    print("\n--- Leadership Comparison ---")
    print(json.dumps(comparison, indent=2))


def example_6_specific_person_research():
    """Example 6: Deep dive on a specific person across their career."""
    print("\n" + "="*80)
    print("EXAMPLE 6: Specific Person Deep Dive")
    print("="*80 + "\n")

    # Research a specific leader
    ticker = "AAPL"
    target_name = "Tim Cook"  # Or any other name

    extractor = LeadershipExtractor()

    # Extract team
    team = extractor.extract_leadership_team(ticker)

    # Find the person
    all_leaders = team.board_of_directors + team.executive_officers
    target = None

    for leader in all_leaders:
        if target_name.lower() in leader.name.lower():
            target = leader
            break

    if not target:
        print(f"Could not find {target_name} in {ticker} leadership")
        return

    print(f"Found: {target.name}")
    print(f"Title: {target.title}")

    # Get detailed profile
    profile = extractor.extract_detailed_profile(
        leader=target,
        ticker=ticker
    )

    # Display comprehensive info
    print(f"\n--- Complete Profile: {profile.name} ---")

    if profile.career_history:
        print(f"\nCareer Timeline:")
        for i, position in enumerate(profile.career_history, 1):
            print(f"  {i}. {position}")

    if profile.education_details:
        print(f"\nEducation:")
        for edu in profile.education_details:
            print(f"  • {edu}")

    if profile.notable_achievements:
        print(f"\nKey Achievements:")
        for achievement in profile.notable_achievements:
            print(f"  • {achievement}")

    if profile.other_current_roles:
        print(f"\nOther Current Roles:")
        for role in profile.other_current_roles:
            print(f"  • {role}")

    if profile.recent_news:
        print(f"\nRecent News:")
        for news in profile.recent_news[:5]:
            print(f"  • {news}")

    if profile.leadership_style:
        print(f"\nLeadership Style:")
        print(f"  {profile.leadership_style}")

    if profile.key_strengths:
        print(f"\nKey Strengths:")
        for strength in profile.key_strengths:
            print(f"  • {strength}")

    if profile.potential_concerns:
        print(f"\nPotential Concerns:")
        for concern in profile.potential_concerns:
            print(f"  • {concern}")


# Interactive mode
def interactive_mode():
    """Interactive mode for custom scripting."""
    print("\n" + "="*80)
    print("INTERACTIVE LEADERSHIP EXTRACTOR")
    print("="*80 + "\n")

    ticker = input("Enter ticker symbol (e.g., AAPL): ").strip().upper()

    print("\nWhat would you like to do?")
    print("1. Extract basic leadership team")
    print("2. Get detailed profiles for all leaders")
    print("3. Full analysis with quality assessment")
    print("4. Research a specific person")

    choice = input("\nEnter choice (1-4): ").strip()

    extractor = LeadershipExtractor()

    if choice == "1":
        team = extractor.extract_leadership_team(ticker)
        print(f"\n✓ Extracted {len(team.board_of_directors + team.executive_officers)} leaders")
        print(f"Results saved to: {extractor.output_dir}/{ticker}_leadership_team.json")

    elif choice == "2":
        profiles = extractor.extract_detailed_profiles(ticker)
        print(f"\n✓ Extracted {len(profiles)} detailed profiles")
        print(f"Results saved to: {extractor.output_dir}/{ticker}_detailed_profiles.json")

    elif choice == "3":
        data = extract_leadership(ticker, detailed=True)
        print(f"\n✓ Complete analysis finished")
        print(f"Results saved to: {extractor.output_dir}/")

    elif choice == "4":
        team = extractor.extract_leadership_team(ticker)
        all_leaders = team.board_of_directors + team.executive_officers

        print("\nAvailable leaders:")
        for i, leader in enumerate(all_leaders, 1):
            print(f"{i}. {leader.name} - {leader.title}")

        person_idx = int(input("\nEnter number: ").strip()) - 1
        if 0 <= person_idx < len(all_leaders):
            leader = all_leaders[person_idx]
            profile = extractor.extract_detailed_profile(leader, ticker)
            print(f"\n✓ Extracted detailed profile for {profile.name}")
            print(json.dumps(profile.model_dump(), indent=2))

    else:
        print("Invalid choice")


if __name__ == "__main__":
    # Run examples
    print("\n" + "#"*80)
    print("# LEADERSHIP EXTRACTOR - EXAMPLE USAGE")
    print("#"*80)

    # Uncomment the examples you want to run:

    example_1_basic_extraction()
    # example_2_detailed_profiles()
    # example_3_full_analysis()
    # example_4_custom_research()
    # example_5_batch_comparison()
    # example_6_specific_person_research()

    # Or run interactive mode:
    # interactive_mode()
