"""Statistics service for tracking dice roll patterns and distributions"""

import json
import os
import datetime
from collections import defaultdict, Counter
from flask import current_app
from ..config import Config

class StatisticsService:
    """Service for computing and tracking roll statistics"""
    
    def __init__(self, config=None):
        self.config = config or Config()
        self.stats_file = os.path.join(self.config.LOG_STORAGE_DIR, "roll_statistics.json")
    
    def analyze_roll_history(self, history_data):
        """Analyze roll history and compute statistics"""
        if not history_data:
            return self._empty_stats()
        
        stats = {
            "total_rolls": len(history_data),
            "roll_distribution": defaultdict(int),
            "table_usage": defaultdict(int),
            "roll_types": defaultdict(int),
            "time_analysis": self._analyze_time_patterns(history_data),
            "dice_analysis": self._analyze_dice_patterns(history_data),
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        # Parse each log entry
        for entry in history_data:
            self._process_log_entry(entry, stats)
        
        # Convert defaultdicts to regular dicts for JSON serialization
        stats["roll_distribution"] = dict(stats["roll_distribution"])
        stats["table_usage"] = dict(stats["table_usage"])
        stats["roll_types"] = dict(stats["roll_types"])
        
        return stats
    
    def _process_log_entry(self, entry, stats):
        """Process a single log entry for statistics"""
        try:
            raw_response = entry.get("raw_response", {})
            raw_payload = entry.get("raw_payload", {})
            
            # Roll value distribution
            roll_value = raw_response.get("rollValue")
            if roll_value is not None:
                stats["roll_distribution"][str(roll_value)] += 1
            
            # Table usage tracking
            roll_type = raw_payload.get("rollType")
            if roll_type:
                stats["roll_types"][roll_type] += 1
                
                if roll_type == "crit":
                    crit_source = raw_payload.get("critSource", "Unknown")
                    damage_type = raw_payload.get("damageType", "Unknown")
                    table_name = f"{crit_source} Crit ({damage_type})"
                    stats["table_usage"][table_name] += 1
                
                elif roll_type == "fumble":
                    fumble_type = raw_payload.get("fumbleType", "Unknown")
                    attack_type = raw_payload.get("attackType", "Unknown")
                    table_name = f"{fumble_type} Fumble ({attack_type})"
                    stats["table_usage"][table_name] += 1
                
        except Exception as e:
            # Log parsing error but don't fail the whole analysis
            try:
                current_app.logger.warning(f"Error parsing log entry for stats: {e}")
            except RuntimeError:
                pass
    
    def _analyze_time_patterns(self, history_data):
        """Analyze temporal patterns in rolls"""
        hourly_distribution = defaultdict(int)
        daily_distribution = defaultdict(int)
        
        for entry in history_data:
            timestamp_str = entry.get("timestamp")
            if not timestamp_str:
                continue
            
            try:
                timestamp = datetime.datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                hour = timestamp.hour
                day = timestamp.strftime('%A')
                
                hourly_distribution[hour] += 1
                daily_distribution[day] += 1
                
            except Exception:
                continue
        
        return {
            "hourly_distribution": dict(hourly_distribution),
            "daily_distribution": dict(daily_distribution)
        }
    
    def _analyze_dice_patterns(self, history_data):
        """Analyze dice roll patterns and streaks"""
        d20_rolls = []
        d100_rolls = []
        
        for entry in history_data:
            raw_response = entry.get("raw_response", {})
            die_type = raw_response.get("dieType")
            roll_value = raw_response.get("rollValue")
            
            if die_type == "d20" and roll_value is not None:
                d20_rolls.append(roll_value)
            elif die_type == "d100" and roll_value is not None:
                d100_rolls.append(roll_value)
        
        return {
            "d20_analysis": self._analyze_die_type(d20_rolls, 20),
            "d100_analysis": self._analyze_die_type(d100_rolls, 100)
        }
    
    def _analyze_die_type(self, rolls, die_max):
        """Analyze patterns for a specific die type"""
        if not rolls:
            return {"count": 0, "average": 0, "distribution": {}}
        
        analysis = {
            "count": len(rolls),
            "average": round(sum(rolls) / len(rolls), 2),
            "min": min(rolls),
            "max": max(rolls),
            "distribution": dict(Counter(rolls)),
            "streaks": self._find_streaks(rolls, die_max)
        }
        
        # Add percentile information
        if die_max == 20:
            analysis["crits"] = len([r for r in rolls if r == 20])
            analysis["fumbles"] = len([r for r in rolls if r == 1])
        
        return analysis
    
    def _find_streaks(self, rolls, die_max):
        """Find interesting streaks in rolls"""
        if len(rolls) < 2:
            return {"longest_high": 0, "longest_low": 0}
        
        high_threshold = die_max * 0.8  # Top 20%
        low_threshold = die_max * 0.2   # Bottom 20%
        
        current_high_streak = 0
        current_low_streak = 0
        longest_high_streak = 0
        longest_low_streak = 0
        
        for roll in rolls:
            if roll >= high_threshold:
                current_high_streak += 1
                current_low_streak = 0
                longest_high_streak = max(longest_high_streak, current_high_streak)
            elif roll <= low_threshold:
                current_low_streak += 1
                current_high_streak = 0
                longest_low_streak = max(longest_low_streak, current_low_streak)
            else:
                current_high_streak = 0
                current_low_streak = 0
        
        return {
            "longest_high": longest_high_streak,
            "longest_low": longest_low_streak
        }
    
    def _empty_stats(self):
        """Return empty statistics structure"""
        return {
            "total_rolls": 0,
            "roll_distribution": {},
            "table_usage": {},
            "roll_types": {},
            "time_analysis": {
                "hourly_distribution": {},
                "daily_distribution": {}
            },
            "dice_analysis": {
                "d20_analysis": {"count": 0, "average": 0, "distribution": {}},
                "d100_analysis": {"count": 0, "average": 0, "distribution": {}}
            },
            "last_updated": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
    
    def get_statistics_from_log(self, logging_service):
        """Get statistics by analyzing the full log file"""
        try:
            # Get raw log data with payload/response info
            log_data = []
            if os.path.exists(logging_service.log_file_path):
                with open(logging_service.log_file_path, "r", encoding="utf-8") as log_file:
                    for line in log_file:
                        try:
                            entry = json.loads(line)
                            log_data.append(entry)
                        except json.JSONDecodeError:
                            continue
            
            return self.analyze_roll_history(log_data)
            
        except Exception as e:
            try:
                current_app.logger.error(f"Error generating statistics: {e}")
            except RuntimeError:
                pass
            return self._empty_stats()
    
    def save_statistics(self, stats):
        """Save statistics to file"""
        try:
            with open(self.stats_file, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except Exception as e:
            try:
                current_app.logger.error(f"Error saving statistics: {e}")
            except RuntimeError:
                pass
    
    def load_cached_statistics(self):
        """Load cached statistics from file"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            try:
                current_app.logger.error(f"Error loading cached statistics: {e}")
            except RuntimeError:
                pass
        return self._empty_stats()