from datetime import datetime
import pytz
from utils import (
    safe_request, success_response, error_response, 
    cache_response, get_qubic_headers
)
from config import (
    QUBIC_API_BASE, APOOL_API_BASE, SOLUTIONS_API_BASE, MINERLAB_API_BASE,
    EXCHANGE_RATE_API, CACHE_DURATION
)
from network_stats import get_network_stats_data, calculate_network_stats

@cache_response(CACHE_DURATION)
def get_tool_data():
    """Get comprehensive data from various sources"""
    try:
        # Initialize response data
        response_data = {}
        
        # 1. Get Tick Overview data
        tick_data = safe_request(
            f"{QUBIC_API_BASE}/Network/TickOverview",
            headers=get_qubic_headers()
        )
        if tick_data:
            response_data.update({
                "currentEpoch": tick_data.get('currentEpoch'),
                "price": str(float(tick_data.get('price', 0)))
            })

        # 2. Get Score data
        score_data = safe_request(
            f"{QUBIC_API_BASE}/Score/Get",
            headers=get_qubic_headers()
        )
        if score_data:
            scores = score_data.get('scores', [])
            total_solutions = sum(score.get('adminScore', 0) for score in scores)
            response_data.update({
                "estimatedIts": int(score_data.get('estimatedIts', 0)),
                "solutionsPerHour": int(score_data.get('solutionsPerHour', 0)),
                "solutionsPerHourCalculated": int(score_data.get('solutionsPerHourCalculated', 0)),
                "total_solutions": total_solutions
            })
        else:
            total_solutions = 0

        # 3. Get exchange rate data
        rate_data = safe_request(EXCHANGE_RATE_API)
        if rate_data:
            response_data["CNY"] = rate_data.get('rates', {}).get('CNY')
        
        # 4. Get idle status
        idle_data = safe_request(f"{SOLUTIONS_API_BASE}/miner_control")
        if idle_data:
            response_data["idle"] = idle_data.get('idle')
        
        # 5. Get pool data
        apool_data = safe_request(f"{APOOL_API_BASE}/index/pool/info", params={'currency': 'qubic'})
        solutions_data = safe_request(f"{SOLUTIONS_API_BASE}/info")
        minerlab_data = safe_request(f"{MINERLAB_API_BASE}/pool_stats?select=*")
        
        # 6. Get proposal data
        proposal_data = safe_request(
            f"{QUBIC_API_BASE}/Voting/Proposal",
            headers=get_qubic_headers()
        )

        # 7. Get network statistics data
        network_stats_data = get_network_stats_data()

        # Build pool hashrate data
        pool_hashrate = {
            "current": {
                "qli_hashrate": int(score_data.get('estimatedIts', 0)) if score_data else None,
                "apool_hashrate": int(float(apool_data.get('result', {}).get('pool_hash', 0))) if apool_data else None,
                "solutions_hashrate": int(float(solutions_data.get('iterrate', 0))) if solutions_data else None,
                "minerlab_hashrate": int(float(minerlab_data[0].get('currentIts', 0))) if minerlab_data and isinstance(minerlab_data, list) and len(minerlab_data) > 0 else None
            }
        }
        
        if network_stats_data:
            averages = network_stats_data.get('averages', {})
            total_records = network_stats_data.get('record_count', 0)
            pool_hashrate.update({
                "average": {
                    "average_qli_hashrate": int(averages.get('average_qli_hashrate', 0)),
                    "average_apool_hashrate": int(averages.get('average_apool_hashrate', 0)),
                    "average_solutions_hashrate": int(averages.get('average_solutions_hashrate', 0)),
                    "average_minerlab_hashrate": int(averages.get('average_minerlab_hashrate', 0)),
                    'record_count': total_records
                }
            })
            
        response_data["pool_hashrate"] = pool_hashrate

        # Add detailed pool data
        if apool_data:
            response_data["apool"] = format_apool_data(apool_data, total_solutions)
        if solutions_data:
            response_data["solutions"] = format_solutions_data(solutions_data, total_solutions)
        if minerlab_data and isinstance(minerlab_data, list) and len(minerlab_data) > 0:
            response_data["minerlab"] = format_minerlab_data(minerlab_data, total_solutions)
        if proposal_data:
            response_data["proposal"] = format_proposal_data(proposal_data)

        return success_response(response_data)

    except Exception as e:
        return error_response(f"Error in get_tool_data: {str(e)}")

def format_apool_data(apool_data, total_solutions):
    """Format Apool data
    
    Args:
        apool_data: Raw data from Apool API
        total_solutions: Total network solutions
    """
    if not apool_data or 'result' not in apool_data:
        return None
    
    result = apool_data['result']
    accepted_solution = result.get('accepted_solution', 0)
    pool_hash = int(float(result.get('pool_hash', 0)))
    total_share = result.get('total_share', 0)
    
    return {
        "accepted_solution": accepted_solution,
        "pool_hash": pool_hash,
        "total_share": total_share,
        "shares_per_solution": int(total_share / accepted_solution) if accepted_solution else 0,
        "corrected_hashrate": int(pool_hash / accepted_solution * total_solutions) if accepted_solution else 0
    }

def format_solutions_data(solutions_data, total_solutions):
    """Format Solutions data
    
    Args:
        solutions_data: Raw data from Solutions API
        total_solutions: Total network solutions
    """
    if not solutions_data:
        return None
    
    solo_solutions = solutions_data.get('solo', {}).get('solutions', 0)
    pplns_solutions = solutions_data.get('pplns', {}).get('solutions', 0)
    accepted_solution = solo_solutions + pplns_solutions
    total_share = solutions_data.get('pplns', {}).get('shares', 0)
    pool_hash = int(float(solutions_data.get('iterrate', 0)))
    
    return {
        "accepted_solution": accepted_solution,
        "solo_solutions": solo_solutions,
        "pplns_solutions": pplns_solutions,
        "pool_hash": pool_hash,
        "total_share": total_share,
        "shares_per_solution": int(total_share / accepted_solution) if accepted_solution else 0,
        "corrected_hashrate": int(pool_hash / accepted_solution * total_solutions) if accepted_solution else 0
    }

def format_minerlab_data(minerlab_data, total_solutions):
    """Format Minerlab data
    
    Args:
        minerlab_data: Raw data from Minerlab API
        total_solutions: Total network solutions
    """
    if not minerlab_data or not isinstance(minerlab_data, list) or len(minerlab_data) == 0:
        return None
    
    # minerlab_data is a list, take the first element
    data = minerlab_data[0]
    accepted_solution = data.get('currentEpochSolutions', 0)
    pool_hash = int(float(data.get('currentIts', 0)))
    
    return {
        "accepted_solution": accepted_solution,
        "pool_hash": pool_hash,
        "corrected_hashrate": int(pool_hash / accepted_solution * total_solutions) if accepted_solution else 0
    }

def format_proposal_data(proposal_data):
    """Format proposal data
    
    Args:
        proposal_data: Raw data from Voting API
    """
    if not proposal_data or not isinstance(proposal_data, list) or len(proposal_data) == 0:
        return None
        
    # Get the latest proposal (assuming list is sorted by time)
    latest_proposal = proposal_data[0]
    
    # Build options information
    options = []
    for option in latest_proposal.get('options', []):
        option_info = {
            'index': option.get('index'),
            'label': option.get('label'),
            'votes': option.get('numberOfVotes', 0)
        }
        if 'value' in option:
            option_info['value'] = option.get('value')
        options.append(option_info)
    
    return {
        "title": latest_proposal.get('title'),
        "totalVotes": latest_proposal.get('totalVotes', 0),
        "url": latest_proposal.get('url'),
        "status": latest_proposal.get('status'),
        "published": latest_proposal.get('published'),
        "epoch": latest_proposal.get('epoch'),
        "proposalType": latest_proposal.get('proposalType'),
        "options": options,
        "hasVotes": latest_proposal.get('hasVotes', False)
    }