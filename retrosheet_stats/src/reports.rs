use std::{any::Any, collections::HashMap, fmt::Display, io::Write};
use smallvec::SmallVec;

use crate::{BallsStrikes, GameRuleOptions, GameSituation, Inning, PlayLineInfo, Report, StatsReport, get_ball_strike_counts_from_pitches, year_from_game_id};

pub struct StatsWinExpectancyReport {
    // value is (num_wins, num_situation)
    stats: HashMap<GameSituation, (u32, u32)>
}
impl StatsWinExpectancyReport {
    pub fn new() -> Self {
        Self { stats: HashMap::new() }
    }
}

impl StatsReport for StatsWinExpectancyReport {
    type Key = GameSituation;
    type Value = (u32, u32);

    fn processed_game_impl(self: &mut Self, _game_id: &str, final_game_situation: &GameSituation,
        situations: &[GameSituation], _play_lines: &[String], _game_rule_options: &GameRuleOptions) {
        // Check the last situation to see who won
        let home_won = final_game_situation.is_home_winning();
        if home_won.is_none() {
            // This game must have been tied when it stopped.  Don't count
            // these stats.
            return;
        }
        let home_won = home_won.unwrap();
        for situation in situations {
            let is_win = if home_won { situation.inning.is_home } else { !situation.inning.is_home };
            // having to use situation.clone() here is unfortunate. But since we're doing this map-reduce
            // style, my guess is that often the key will not be in the HashMap, and this avoids doing two lookups
            // in the HashMap.
            let entry = self.stats.entry(situation.clone()).or_insert((0, 0));
            if is_win {
                entry.0 += 1;
            }
            entry.1 += 1;
        }
    }

    fn get_stats<'a>(&'a self) -> &'a HashMap<Self::Key, Self::Value> { &self.stats }
    fn write_key<T:Write>(&self, file: &mut T, key: &Self::Key) {
        write!(file, "({}, {}, {}, ({}, {}, {}), {})",
            key.inning.number, key.inning.is_home as i32, key.outs, key.runners[0] as i32, key.runners[1] as i32, key.runners[2] as i32, key.cur_score_diff).unwrap();
    }
    fn write_value<T:Write>(&self, file: &mut T, value: &Self::Value) {
        write!(file, "({}, {})", value.0, value.1).unwrap();
    }
    fn report_file_name() -> &'static str { "stats" }

    fn make_new_impl(&self) -> Box<dyn Report> { Box::new(Self::new()) }

    fn name_impl(&self) -> &'static str { "StatsWinExpectancyReport" }

    fn clear_stats_impl(self: &mut Self) { self.stats.clear(); }

    fn merge_into_impl(self: &Self, other: &mut dyn Any) {
        let other = other.downcast_mut::<Self>().unwrap();
        for entry in self.stats.iter() {
            let other_entry = other.stats.entry(*entry.0).or_insert((0, 0));
            other_entry.0 += entry.1.0;
            other_entry.1 += entry.1.1;
        }
    }
}

pub struct StatsWinExpectancyWithBallsStrikesReport {
    // value is (num_wins, num_situation)
    stats: HashMap<(GameSituation, BallsStrikes), (u32, u32)>
}
impl StatsWinExpectancyWithBallsStrikesReport {
    pub fn new() -> Self {
        Self { stats: HashMap::new() }
    }
}

impl StatsReport for StatsWinExpectancyWithBallsStrikesReport {
    type Key = (GameSituation, BallsStrikes);
    type Value = (u32, u32);
    fn clear_stats_impl(&mut self) { self.stats.clear(); }
    fn processed_game_impl(self: &mut Self, _game_id: &str, final_game_situation: &GameSituation,
        situations: &[GameSituation], play_lines: &[String], _game_rule_options: &GameRuleOptions) {
        // Check the last situation to see who won
        let home_won = final_game_situation.is_home_winning();
        if home_won.is_none() {
            // This game must have been tied when it stopped.  Don't count
            // these stats.
            return;
        }
        let home_won = home_won.unwrap();
        for (i, situation) in situations.iter().enumerate() {
            let is_win = if home_won { situation.inning.is_home } else { !situation.inning.is_home };
            let pitches = PlayLineInfo::from(&play_lines[i][..]).pitches_str;
            let counts = get_ball_strike_counts_from_pitches(pitches);
            for count in counts {
                if count.balls < 4 && count.strikes < 3 {
                    let entry = self.stats.entry((situation.clone(), count))
                        .or_insert((0, 0));
                    if is_win {
                        entry.0 += 1;
                    }
                    entry.1 += 1;
                }
            }
        }
    }
    fn merge_into_impl(self: &Self, other: &mut dyn Any) { 
        let other = other.downcast_mut::<Self>().unwrap();
        for entry in self.stats.iter() {
            let other_entry = other.stats.entry(*entry.0).or_insert((0, 0));
            other_entry.0 += entry.1.0;
            other_entry.1 += entry.1.1;
        }
    }

    fn name_impl(&self) -> &'static str { "StatsWinExpectancyWithBallsStrikesReport" }

    fn make_new_impl(&self) -> Box<dyn Report> { Box::new(Self::new()) }

    fn get_stats<'a>(&'a self) -> &'a HashMap<Self::Key, Self::Value> { &self.stats }
    fn write_key<T:Write>(&self, file: &mut T, key: &Self::Key) {
        write!(file, "({}, {}, {}, ({}, {}, {}), {}, ({}, {}))",
            key.0.inning.number, key.0.inning.is_home as i32, key.0.outs, key.0.runners[0] as i32, key.0.runners[1] as i32, key.0.runners[2] as i32, key.0.cur_score_diff,
            key.1.balls, key.1.strikes).unwrap();
    }
    fn write_value<T:Write>(&self, file: &mut T, value: &Self::Value) {
        write!(file, "({}, {})", value.0, value.1).unwrap();
    }
    fn report_file_name() -> &'static str { "statswithballsstrikes" }
}

pub struct StatsRunExpectancyPerInningWithBallsStrikesReport {
    // key is (outs, runners, balls/strikes)
    // value is times that index of runs were gained
    // so a value of [10, 7, 4] means that 10 times 0 runs were scored,
    // 7 times 1 run was scored, and 4 times 2 runs were scored
    stats: HashMap<(u8, [bool;3], BallsStrikes), Vec<u32>>
}
impl StatsRunExpectancyPerInningWithBallsStrikesReport {
    pub fn new() -> Self {
        Self { stats: HashMap::new() }
    }
}

impl StatsReport for StatsRunExpectancyPerInningWithBallsStrikesReport {
    type Key = (u8, [bool;3], BallsStrikes);
    type Value = Vec<u32>;

    fn get_stats<'a>(&'a self) -> &'a HashMap<Self::Key, Self::Value> { &self.stats }
    fn write_key<T:Write>(&self, file: &mut T, key: &Self::Key) {
        write!(file, "({}, ({}, {}, {}), ({}, {}))", key.0, key.1[0] as i32, key.1[1] as i32, key.1[2] as i32, key.2.balls, key.2.strikes).unwrap();
    }

    fn write_value<T:Write>(&self, file: &mut T, key: &Self::Value) {
        write!(file, "{}", format_vec_default(key)).unwrap();
    }

    fn report_file_name() -> &'static str { "runsperinningballsstrikesstats" }
    fn make_new_impl(&self) -> Box<dyn Report> { Box::new(Self::new()) }
    fn name_impl(&self) -> &'static str { "StatsRunExpectancyPerInningWithBallsStrikesReport" }
    fn processed_game_impl(self: &mut Self, _game_id: &str, final_game_situation: &GameSituation,
        situations: &[GameSituation], play_lines: &[String], _game_rule_options: &GameRuleOptions) {
        let mut innings_to_keys = HashMap::<Inning, Vec<(&GameSituation, Vec<BallsStrikes>)>>::new();
        for (index, situation) in situations.iter().enumerate() {
            // add stuff
            let mut balls_strikes_vec = vec![];
            let pitches = PlayLineInfo::from(&play_lines[index][..]).pitches_str;
            let counts = get_ball_strike_counts_from_pitches(pitches);
            for count in counts {
                if count.balls < 4 && count.strikes < 3 {
                    // TODO - simplify this
                    balls_strikes_vec.push(count);
                }
            }
            let entry = innings_to_keys.entry(situation.inning).or_insert(vec![]);
            entry.push((situation, balls_strikes_vec));
        }
        for (inning, situations) in innings_to_keys.iter() {
            let starting_run_diff = situations.first().unwrap().0.cur_score_diff;
            let mut ending_run_diff = 
                if let Some(next_situations) = innings_to_keys.get(&inning.next_inning()) {
                    -1 * next_situations[0].0.cur_score_diff
                }
                else {
                    situations.last().unwrap().0.cur_score_diff
                };
            if &final_game_situation.inning == inning {
                ending_run_diff = final_game_situation.cur_score_diff;
            }
            assert!(ending_run_diff - starting_run_diff >= 0, "uh-oh, scored {} runs!", ending_run_diff - starting_run_diff);
            // Add the statistics now
            for situation in situations {
                // Make sure we don't duplicate keys
                let runs_gained = (ending_run_diff - situation.0.cur_score_diff) as usize;
                for count in &situation.1 {
                    let key_to_use = (situation.0.outs, situation.0.runners, *count);
                    let run_diff_vec = self.stats.entry(key_to_use).or_default();
                    if run_diff_vec.len() < runs_gained + 1 {
                        run_diff_vec.resize(runs_gained + 1, 0);
                    }
                    *run_diff_vec.get_mut(runs_gained).unwrap() += 1;
                }
            }
        }
    }
    fn clear_stats_impl(&mut self) { self.stats.clear(); }

    fn merge_into_impl(self: &Self, other: &mut dyn Any) { 
        let other = other.downcast_mut::<Self>().unwrap();
        for entry in self.stats.iter() {
            let other_entry = other.stats.entry(*entry.0).or_default();
            if other_entry.len() < entry.1.len() {
                other_entry.resize(entry.1.len(), 0);
            }
            for i in 0..entry.1.len() {
                other_entry[i] += entry.1[i];
            }
        }
    }
}

pub struct StatsRunExpectancyPerInningReport {
    // key is (outs, runners)
    // value is times that index of runs were gained
    // so a value of [10, 7, 4] means that 10 times 0 runs were scored,
    // 7 times 1 run was scored, and 4 times 2 runs were scored
    stats: HashMap<(u8, [bool;3]), Vec<u32>>
}
impl StatsRunExpectancyPerInningReport {
    pub fn new() -> Self {
        Self { stats: HashMap::new() }
    }
}

impl StatsReport for StatsRunExpectancyPerInningReport {
    type Key = (u8, [bool;3]);
    type Value = Vec<u32>;

    fn clear_stats_impl(&mut self) { self.stats.clear(); }
    fn processed_game_impl(self: &mut Self, _game_id: &str, final_game_situation: &GameSituation,
        situations: &[GameSituation], _play_lines: &[String], _game_rule_options: &GameRuleOptions) {
        let mut innings_to_keys = HashMap::<Inning, &[GameSituation]>::new();
        let mut cur_inning = Inning::new();
        let mut start_situation = 0;
        for (index, situation) in situations.iter().enumerate() {
            if situation.inning != cur_inning {
                assert_ne!(start_situation, index);
                // add stuff
                if let Some(_) = innings_to_keys.insert(cur_inning, &situations[start_situation..index]) {
                    assert!(false, "got duplicate innings_to_keys for game {} inning {:?} new inning {:?}", _game_id, cur_inning, situation.inning);
                }
                cur_inning = situation.inning;
                start_situation = index;
            }
        }
        if start_situation < situations.len() {
            innings_to_keys.insert(cur_inning, &situations[start_situation..]);
        }
        for (inning, &situations) in innings_to_keys.iter() {
            let starting_run_diff = situations.first().unwrap().cur_score_diff;
            let mut ending_run_diff = 
                if let Some(&next_situations) = innings_to_keys.get(&inning.next_inning()) {
                    -1 * next_situations[0].cur_score_diff
                }
                else {
                    situations.last().unwrap().cur_score_diff
                };
            if &final_game_situation.inning == inning {
                ending_run_diff = final_game_situation.cur_score_diff;
            }
            assert!(ending_run_diff - starting_run_diff >= 0, "uh-oh, scored {} runs!", ending_run_diff - starting_run_diff);
            // Add the statistics now
            for situation in situations {
                // Make sure we don't duplicate keys
                let key_to_use = (situation.outs, situation.runners);
                let runs_gained = (ending_run_diff - situation.cur_score_diff) as usize;
                let run_diff_vec = self.stats.entry(key_to_use).or_default();
                if run_diff_vec.len() < runs_gained + 1 {
                    run_diff_vec.resize(runs_gained + 1, 0);
                }
                *run_diff_vec.get_mut(runs_gained).unwrap() += 1;
            }
        }
    }

    fn merge_into_impl(self: &Self, other: &mut dyn Any) { 
        let other = other.downcast_mut::<Self>().unwrap();
        for entry in self.stats.iter() {
            let other_entry = other.stats.entry(*entry.0).or_default();
            if other_entry.len() < entry.1.len() {
                other_entry.resize(entry.1.len(), 0);
            }
            for i in 0..entry.1.len() {
                other_entry[i] += entry.1[i];
            }
        }
    }

    fn name_impl(&self) -> &'static str { "StatsRunExpectancyPerInningReport" }
    fn make_new_impl(&self) -> Box<dyn Report> { Box::new(Self::new()) }
    fn get_stats<'a>(&'a self) -> &'a HashMap<Self::Key, Self::Value> { &self.stats }
    fn write_key<T:Write>(&self, file: &mut T, key: &Self::Key) {
        write!(file, "({}, ({}, {}, {}))", key.0, key.1[0] as i32, key.1[1] as i32, key.1[2] as i32).unwrap();
    }
    fn write_value<T:Write>(&self, file: &mut T, key: &Self::Value) {
        write!(file, "{}", format_vec_default(key)).unwrap();
    }

    fn report_file_name() -> &'static str { "runsperinningstats" }
}

// Finds games where the home team won after being down by 6 runs in the bottom of the ninth
// with two outs and nobody on base
pub struct HomeTeamDownSixWithTwoOutsInNinthReport {
    game_ids: Vec<String>
}
impl HomeTeamDownSixWithTwoOutsInNinthReport {
    pub fn new() -> Self {
        Self { game_ids: Vec::new() }
    }
}
impl Report for HomeTeamDownSixWithTwoOutsInNinthReport {
    fn processed_game(self: &mut Self, game_id: &str, final_game_situation: &GameSituation,
        situations: &[GameSituation], _play_lines: &[String], _game_rule_options: &GameRuleOptions) {
        // Check the last situation to see who won
        let home_won = final_game_situation.is_home_winning();
        if let Some(true) = home_won {
            if situations.contains(&GameSituation {
                inning: Inning { number: 9, is_home: true },
                outs: 2,
                runners: [false, false, false],
                cur_score_diff: -6
            }) {
                self.game_ids.push(game_id.to_owned());
            }
        }
    }

    fn clear_stats(self: &mut Self) {
        self.game_ids.clear();
    }

    fn done_with_year(self: &mut Self, _year: usize) {
        panic!("{} doesn't support by year", self.name());
    }

    fn done_with_all(self: &mut Self) {
        self.game_ids.sort();
        for game_id in self.game_ids.iter() {
            println!("GOT IT with id {}", game_id);
        }
    }

    fn make_new(&self) -> Box<dyn Report> {
        Box::new(Self::new())
    }

    fn name(&self) -> &'static str {
        "HomeTeamDownSixWithTwoOutsInNinthReport"
    }

    fn as_any_mut(&mut self) -> &mut dyn Any {
        self
    }

    fn merge_into(self: &Self, other: &mut dyn Any) { 
        let other = other.downcast_mut::<Self>().unwrap();
        for id in self.game_ids.iter() {
            other.game_ids.push(id.to_owned());
        }
    }
}
// Finds games with a specific set of situation keys. Useful for debugging purposes
pub struct SpecificSituationKeysReport {
    required_keys: Vec<GameSituation>,
    game_ids_and_situations: Vec<(String, Vec<GameSituation>)>
}
impl SpecificSituationKeysReport {
    pub fn new() -> Self {
        // Try to look for unusual situations to include here so hopefully there will be only one game
        // that satisfies all of them.
        let required_keys = vec![
            GameSituation { inning: Inning { number: 13, is_home: true}, outs: 0, runners: [true, true, false], cur_score_diff: 0},
            GameSituation { inning: Inning { number: 13, is_home: true}, outs: 0, runners: [true, false, false], cur_score_diff: 0},
            GameSituation { inning: Inning { number: 13, is_home: false}, outs: 1, runners: [false, true, false], cur_score_diff: 0},
            GameSituation { inning: Inning { number: 12, is_home: false}, outs: 2, runners: [false, true, true], cur_score_diff: 0},
            GameSituation { inning: Inning { number: 11, is_home: false}, outs: 2, runners: [true, true, true], cur_score_diff: 0},
            GameSituation { inning: Inning { number: 7, is_home: false}, outs: 2, runners: [true, false, true], cur_score_diff: 0},
            GameSituation { inning: Inning { number: 6, is_home: true}, outs: 2, runners: [false, false, true], cur_score_diff: 0},
        ];

        Self { game_ids_and_situations: Vec::new(), required_keys }
    }
}
impl Report for SpecificSituationKeysReport {
    fn processed_game(self: &mut Self, game_id: &str, _final_game_situation: &GameSituation,
        situations: &[GameSituation], _play_lines: &[String], _game_rule_options: &GameRuleOptions) {
        for required_key in self.required_keys.iter() {
            if !situations.contains(required_key) {
                return;
            }
        }
        self.game_ids_and_situations.push(
            (game_id.to_owned(), situations.to_owned())
        );
    }

    fn clear_stats(self: &mut Self) {
        self.game_ids_and_situations.clear();
    }

    fn done_with_year(self: &mut Self, _year: usize) {
        panic!("{} doesn't support by year", self.name());
    }

    fn done_with_all(self: &mut Self) {
        self.game_ids_and_situations.sort();
        for game_id_and_situation in self.game_ids_and_situations.iter() {
            println!("game id {}", game_id_and_situation.0);
            for situation in game_id_and_situation.1.iter() {
                println!("  {:?}", situation);
            }
        }
    }

    fn make_new(&self) -> Box<dyn Report> {
        Box::new(Self::new())
    }

    fn name(&self) -> &'static str {
        "SpecificSituationKeysReport"
    }

    fn as_any_mut(&mut self) -> &mut dyn Any {
        self
    }

    fn merge_into(self: &Self, other: &mut dyn Any) { 
        let other = other.downcast_mut::<Self>().unwrap();
        for id_and_situation in self.game_ids_and_situations.iter() {
            other.game_ids_and_situations.push(id_and_situation.clone());
        }
    }
}

pub struct WalkOffWalkReport {
    num_games: u32,
    num_games_with_pitches: u32,
    walk_off_walks: u32,
    walk_off_walks_on_four_pitches: u32,
    year_count: HashMap<u32, u32>,
    walk_off_walks_on_four_pitches_lines: Vec<String>
}
impl WalkOffWalkReport {
    pub fn new() -> Self {
        Self {
            num_games: 0,
            num_games_with_pitches: 0,
            walk_off_walks: 0,
            walk_off_walks_on_four_pitches: 0,
            year_count: HashMap::new(),
            walk_off_walks_on_four_pitches_lines: Vec::new()
        }
    }
}
impl Report for WalkOffWalkReport {
    fn processed_game(self: &mut Self, game_id: &str, final_game_situation: &GameSituation,
        situations: &[GameSituation], play_lines: &[String], _game_rule_options: &GameRuleOptions) {
        let year: u32 = year_from_game_id(game_id);
        self.year_count.entry(year).or_insert(0);
        let last_game_situation = situations.last().unwrap();
        let home_won = final_game_situation.is_home_winning();
        if home_won.is_none() {
            // This game must have been tied when it stopped.  Don't count
            // these stats.
            return
        }
        let home_won = home_won.unwrap();

        self.num_games += 1;
        let last_play_line = play_lines.last().unwrap();
        let last_play_line_info: PlayLineInfo = last_play_line[..].into();
        let pitches = last_play_line_info.pitches_str;
        if pitches.chars().any(|c| c != '?') {
            self.num_games_with_pitches += 1;
        }
        if !home_won {
            // walk-offs mean the home team won
            return;
        }
        if last_game_situation.inning.is_home &&
        last_game_situation.outs <= 2 &&
        last_game_situation.runners == [true, true, true] &&
        last_game_situation.cur_score_diff == 0 {

            // TODO - refactor to use main parsing?
            let play_string = &last_play_line_info.play_str;
            let play_array: SmallVec<[&str;2]> = play_string.split('.').collect();
            if play_array.len() > 2 {
                //return Err(anyhow!("play_array is too long after splitting on '.': \"{}\"", play_string));
                return;
            }
            let batter_events = play_array[0].split(';');
            for batter_event in batter_events {
                let batter_event = batter_event.trim();
                if (batter_event.starts_with("W") && !batter_event.starts_with("WP")) || batter_event.starts_with("I") {
                    // walk
                    self.walk_off_walks += 1;
                    self.year_count.entry(year).and_modify(|x| *x += 1);
                    let counts = get_ball_strike_counts_from_pitches(&pitches);
                    let last_count = counts.last().unwrap();
                    if last_count.balls == 4 && last_count.strikes == 0 {
                        self.walk_off_walks_on_four_pitches += 1;
                        self.walk_off_walks_on_four_pitches_lines.push(format!("{}: {}", game_id, last_play_line));
                    }
                }
            }
        }
    }

    fn clear_stats(self: &mut Self) { }

    fn merge_into(self: &Self, other: &mut dyn Any) {
        let other = other.downcast_mut::<Self>().unwrap();
        other.num_games += self.num_games;
        other.num_games_with_pitches += self.num_games_with_pitches;
        other.walk_off_walks += self.walk_off_walks;
        other.walk_off_walks_on_four_pitches += self.walk_off_walks_on_four_pitches;
        for (year, count) in &self.year_count {
            *other.year_count.entry(*year).or_default() += count;
        }
    }

    fn done_with_year(self: &mut Self, _year: usize) {
        panic!("{} doesn't support year by year", self.name());
    }

    fn done_with_all(self: &mut Self) {
        println!("num_games: {}", self.num_games);
        println!("num_games_with_pitches: {}", self.num_games_with_pitches);
        println!("walk off walks: {}", self.walk_off_walks);
        println!("walk off walks on four pitches: {}", self.walk_off_walks_on_four_pitches);
        let mut years = self.year_count.keys().collect::<Vec<_>>();
        years.sort();
        for year in years {
            println!("  {}: {}", year, self.year_count[year]);
        }
    }

    fn make_new(&self) -> Box<dyn Report> {
        Box::new(Self::new())
    }

    fn name(&self) -> &'static str {
        "WalkOffWalkReport"
    }

    fn as_any_mut(&mut self) -> &mut dyn Any {
        self
    }
}

pub struct CountsToWalksAndStrikeoutsStats {
    total: u32,
    walks: u32,
    strikeouts: u32
}
impl CountsToWalksAndStrikeoutsStats {
    pub fn new() -> Self {
        Self {
            total: 0,
            walks: 0,
            strikeouts: 0
        }
    }
}
impl Display for CountsToWalksAndStrikeoutsStats {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        let walk_percent = (100.0 * self.walks as f32) / self.total as f32;
        let strikeout_percent = (100.0 * self.strikeouts as f32) / self.total as f32;
        f.write_fmt(format_args!("total: {} walks: {} strikeouts: {} walk%: {:.2} strikeout%: {:.2}", self.total, self.walks, self.strikeouts, walk_percent, strikeout_percent))
    }
}

pub struct CountsToWalksAndStrikeoutsReport {
    num_games: u32,
    count_stats: HashMap<BallsStrikes, CountsToWalksAndStrikeoutsStats>,
    year_count: HashMap<u32, u32>
}

impl CountsToWalksAndStrikeoutsReport {
    pub fn new() -> Self {
        Self {
            num_games: 0,
            count_stats: HashMap::new(),
            year_count: HashMap::new()
        }
    }
}

impl Report for CountsToWalksAndStrikeoutsReport {
    fn processed_game(self: &mut Self, game_id: &str, _final_game_situation: &GameSituation,
        _situations: &[GameSituation], play_lines: &[String], _game_rule_options: &GameRuleOptions) {
        self.num_games += 1;
        let year: u32 = year_from_game_id(game_id);
        for play_line in play_lines {
            let info = PlayLineInfo::from(&play_line[..]);
            let pitches = info.pitches_str;
            if !pitches.chars().any(|c| c != '?') {
                continue;
            }
            let year_count = self.year_count.entry(year).or_insert(0);
            *year_count += 1;

            let all_counts = get_ball_strike_counts_from_pitches(pitches);
            let last_count = all_counts.last().unwrap();
            let is_walk = last_count.balls == 4;
            let is_strikeout = last_count.strikes == 3;
            for count in all_counts {
                let stats = self.count_stats.entry(count).or_insert(CountsToWalksAndStrikeoutsStats::new());
                stats.total += 1;
                if is_walk {
                    stats.walks += 1;
                }
                else if is_strikeout {
                    stats.strikeouts += 1;
                }
            }
        }
    }

    fn clear_stats(self: &mut Self) { }

    fn merge_into(self: &Self, other: &mut dyn Any) {
        let other = other.downcast_mut::<Self>().unwrap();
        other.num_games = self.num_games;
        for (key, value) in self.count_stats.iter() {
            let stats = other.count_stats.entry(*key).or_insert(CountsToWalksAndStrikeoutsStats::new());
            stats.total += value.total;
            stats.walks += value.walks;
            stats.strikeouts += value.strikeouts;
        }
        for (key, value) in self.year_count.iter() {
            let other_entry = other.year_count.entry(*key).or_insert(0);
            *other_entry += value;
        }
    }

    fn done_with_year(self: &mut Self, _year: usize) { panic!("Doesn't support by year") }

    fn done_with_all(self: &mut Self) {
        println!("num_games: {}", self.num_games);
        let mut counts: Vec<_> = self.count_stats.keys().collect();
        counts.sort();
        for count in counts {
            if count.balls < 4 && count.strikes < 3 {
                println!("{}: {}", count, self.count_stats[count]);
            }
        }
        let mut years: Vec<_> = self.year_count.keys().collect();
        years.sort();
        for year in years {
            println!("PAs in {}: {}", year, self.year_count[year]);
        }
    }

    fn make_new(&self) -> Box<dyn Report> { Box::new(Self::new()) }

    fn name(&self) -> &'static str { "CountsToWalksAndStrikeoutsReport" }

    fn as_any_mut(&mut self) -> &mut dyn Any { self }
}

pub struct BasesLoadedNoOutsNoRunsReport {
    num_situations: u32,
    num_zero_runs: u32
}
impl BasesLoadedNoOutsNoRunsReport {
    pub fn new() -> Self {
        Self {
            num_situations: 0,
            num_zero_runs: 0
        }
    }
}

impl Report for BasesLoadedNoOutsNoRunsReport {
    fn processed_game(self: &mut Self, _game_id: &str, _final_game_situation: &GameSituation,
        situations: &[GameSituation], _play_lines: &[String], _game_rule_options: &GameRuleOptions) {
        let mut innings_to_situations: HashMap<Inning, Vec<&GameSituation>> = HashMap::new();
        for situation in situations {
            let vec = innings_to_situations.entry(situation.inning).or_insert(vec![]);
            vec.push(situation);
        }
        for (inning, situations) in innings_to_situations.iter() {
            let next_inning = inning.next_inning();
            let next_inning_situations = innings_to_situations.get(&next_inning);
            let ending_run_diff = match next_inning_situations {
                Some(next_inning_situations) => -1 * next_inning_situations.first().unwrap().cur_score_diff,
                None => situations.last().unwrap().cur_score_diff
            };
            // Add the statistics now
            for situation in situations {
                if situation.runners == [true, true, true] && situation.outs == 0 {
                    self.num_situations += 1;
                    if ending_run_diff - situation.cur_score_diff == 0 {
                        self.num_zero_runs += 1;
                    }
                }
            }
        }
    }

    fn clear_stats(self: &mut Self) {
        self.num_situations = 0;
        self.num_zero_runs = 0;
    }

    fn merge_into(self: &Self, other: &mut dyn Any) {
        let other = other.downcast_mut::<Self>().unwrap();
        other.num_situations += self.num_situations;
        other.num_zero_runs += self.num_zero_runs;
    }

    fn done_with_year(self: &mut Self, year: usize) {
        println!("{}|{}|{}|{:.2}", year, self.num_situations, self.num_zero_runs, 100.0 * (self.num_zero_runs as f32/ self.num_situations as f32));
    }

    fn done_with_all(self: &mut Self) {
        println!("{}|{}|{:.2}", self.num_situations, self.num_zero_runs, 100.0 * (self.num_zero_runs as f32/ self.num_situations as f32));
    }

    fn make_new(&self) -> Box<dyn Report> {
        Box::new(Self::new())
    }

    fn name(&self) -> &'static str { "BasesLoadedNoOutsNoRunsReport" }

    fn as_any_mut(&mut self) -> &mut dyn Any { self }
}

fn process_game_run_expectancy_by_inning<'a, T>(game_id: &str, final_game_situation: &GameSituation, situations: &[GameSituation],
    game_rule_options: &GameRuleOptions, mut process_run_diff_vec: T)
    where T: FnMut(Inning, usize, Box<dyn FnMut(&mut Vec<u32>, usize)>) {
    // In 2020 some games (doubleheaders) were played with only 7 innings, skip these
    // to avoid messing up statistics.
    if game_rule_options.innings != 9 {
        return;
    }
    // In 2020 extra innings started a runner on second base, which messes up
    // statistics.  If this rule continues we should figure out how to handle this,
    // but for now, skip these games.
    // don't use final_game_situation here, because if the visiting team wins a normal 9 inning game
    // final_game_situation will be the top of the 10th inning (with 0 outs)
    let last_real_situation = situations[situations.len() - 1];
    if game_rule_options.runner_starts_on_second_in_extra_innings && last_real_situation.inning.number > 9 {
        return;
    }

    let mut innings_to_keys = HashMap::<Inning, &[GameSituation]>::new();
    let mut cur_inning = Inning::new();
    let mut start_situation = 0;
    for (index, situation) in situations.iter().enumerate() {
        if situation.inning != cur_inning {
            assert_ne!(start_situation, index);
            // add stuff
            if let Some(_) = innings_to_keys.insert(cur_inning, &situations[start_situation..index]) {
                assert!(false, "got duplicate innings_to_keys for game {} inning {:?} new inning {:?}", game_id, cur_inning, situation.inning);
            }
            cur_inning = situation.inning;
            start_situation = index;
        }
    }
    if start_situation < situations.len() {
        innings_to_keys.insert(cur_inning, &situations[start_situation..]);
    }
    for (inning, &situations) in innings_to_keys.iter() {
        let starting_run_diff = situations.first().unwrap().cur_score_diff;
        let mut ending_run_diff = 
            if let Some(&next_situations) = innings_to_keys.get(&inning.next_inning()) {
                -1 * next_situations[0].cur_score_diff
            }
            else {
                situations.last().unwrap().cur_score_diff
            };
        if &final_game_situation.inning == inning {
            ending_run_diff = final_game_situation.cur_score_diff;
        }
        assert!(ending_run_diff - starting_run_diff >= 0, "uh-oh, scored {} runs!", ending_run_diff - starting_run_diff);
        let runs_gained = (ending_run_diff - starting_run_diff) as usize;
        // This would be better perf (since we don't allocate a new Box every time),
        // but can't be shared between threads safely.
        // I think it actually is safe but am not sure how to convince the compiler of that.
        /*lazy_static! {
            static ref ADD_RUN_TO_DIFF_VEC : Box<dyn FnMut(&mut Vec<u32>)> = 
                Box::new(|run_diff_vec| {
                    if run_diff_vec.len() < runs_gained + 1 {
                        run_diff_vec.resize(runs_gained + 1, 0);
                    }
                    *run_diff_vec.get_mut(runs_gained).unwrap() += 1;
                });
        }*/
        process_run_diff_vec(*inning, runs_gained, Box::new(|run_diff_vec, runs_gained| {
            if run_diff_vec.len() < runs_gained + 1 {
                run_diff_vec.resize(runs_gained + 1, 0);
            }
            *run_diff_vec.get_mut(runs_gained).unwrap() += 1;
        }));
    }
}

fn write_extra_run_expectancy_by_inning_info<T: Write>(file: &mut T, value: &Vec<u32>) {
    let total: u32 = value.iter().sum();
    writeln!(file, "total: {}", total).unwrap();
    let weighted_total: u32 = value.iter().enumerate().map(|(i, val)| (i as u32) * val).sum();
    let expected_value: f32 = (weighted_total as f32)/(total as f32);
    writeln!(file, "expected value: {}", expected_value).unwrap();
    let percentages  = value.iter().map(|&val| (val as f32 * 100f32)/(total as f32));
    writeln!(file, "{}", format_vec(&percentages.collect::<Vec<f32>>(), |p| format!("{:.2}%", p))).unwrap();
    let weighted_contributions = value.iter().enumerate().map(|(i, val)| ((i as f32) * (*val as f32))/(total as f32));
    writeln!(file, "contribs: {}", format_vec(&weighted_contributions.collect::<Vec<f32>>(), |p| format!("{:.2}", p))).unwrap();
    writeln!(file, "").unwrap();
}

pub struct StatsRunExpectancyPerInningByInningReport {
    // key is inning
    // value is times that index of runs were gained
    // so a value of [10, 7, 4] means that 10 times 0 runs were scored,
    // 7 times 1 run was scored, and 4 times 2 runs were scored
    stats: HashMap<Inning, Vec<u32>>
}
impl StatsRunExpectancyPerInningByInningReport {
    pub fn new() -> Self {
        Self { stats: HashMap::new() }
    }
}

impl StatsReport for StatsRunExpectancyPerInningByInningReport {
    type Key = Inning;
    type Value = Vec<u32>;

    fn clear_stats_impl(&mut self) { self.stats.clear(); }
    fn processed_game_impl(self: &mut Self, game_id: &str, final_game_situation: &GameSituation,
        situations: &[GameSituation], _play_lines: &[String], game_rule_options: &GameRuleOptions) {
        // walkoff
        /*if _game_id == "HOU201910190" {
            for situation in situations {
                println!("{:?}", situation);
            }
            println!("final: {:?}", final_game_situation);
        }*/
        process_game_run_expectancy_by_inning(game_id, final_game_situation, situations,
            game_rule_options,
             |inning, runs_gained, mut process_fn| process_fn(self.stats.entry(inning).or_default(), runs_gained));
    }

    fn merge_into_impl(self: &Self, other: &mut dyn Any) { 
        let other = other.downcast_mut::<Self>().unwrap();
        for entry in self.stats.iter() {
            let other_entry = other.stats.entry(*entry.0).or_default();
            if other_entry.len() < entry.1.len() {
                other_entry.resize(entry.1.len(), 0);
            }
            for i in 0..entry.1.len() {
                other_entry[i] += entry.1[i];
            }
        }
    }

    fn name_impl(&self) -> &'static str { "StatsRunExpectancyPerInningByInningReport" }
    fn make_new_impl(&self) -> Box<dyn Report> { Box::new(Self::new()) }
    fn get_stats<'a>(&'a self) -> &'a HashMap<Self::Key, Self::Value> { &self.stats }
    fn write_key<T:Write>(&self, file: &mut T, key: &Self::Key) {
        write!(file, "({}, {})", key.number, key.is_home).unwrap();
    }
    fn write_value<T:Write>(&self, file: &mut T, value: &Self::Value) {
        write!(file, "{}", format_vec_default(value)).unwrap();
    }
    fn write_extra<T:Write>(&self, file: &mut T, _key: &Self::Key, value: &Self::Value) {
        write_extra_run_expectancy_by_inning_info(file, value);
    }

    fn report_file_name() -> &'static str { "analysis/runsByInning/runsperinningbyinningstats" }
}

// https://thesportjournal.org/article/examining-perceptions-of-baseballs-eras/
// see also https://www.billjamesonline.com/dividing_baseball_history_into_eras/ (but didn't use)
#[derive(Debug, Clone, Copy, PartialEq, PartialOrd, Ord, Eq, Hash)]
pub enum Era {
    Expansion,
    FreeAgency,
    Steroid,
    PostSteroid
}

impl From<u32> for Era {
    fn from(year: u32) -> Self {
        match year {
            0..=1976 => Era::Expansion, // technically this is 1961-1976, but we only have a few years before this, so include those too
            1977..=1993 => Era::FreeAgency,
            1994..=2005 => Era::Steroid,
            _ => Era::PostSteroid
        }
    }
}

impl Display for Era {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        write!(f, "{:?}", self)
    }
}

pub struct StatsRunExpectancyPerInningByInningAndEraReport {
    // key is inning
    // value is times that index of runs were gained
    // so a value of [10, 7, 4] means that 10 times 0 runs were scored,
    // 7 times 1 run was scored, and 4 times 2 runs were scored
    stats: HashMap<(Inning, Era), Vec<u32>>
}
impl StatsRunExpectancyPerInningByInningAndEraReport {
    pub fn new() -> Self {
        Self { stats: HashMap::new() }
    }
}
impl StatsReport for StatsRunExpectancyPerInningByInningAndEraReport {
    type Key = (Inning, Era);
    type Value = Vec<u32>;

    fn clear_stats_impl(&mut self) { self.stats.clear(); }
    fn processed_game_impl(self: &mut Self, game_id: &str, final_game_situation: &GameSituation,
        situations: &[GameSituation], _play_lines: &[String], game_rule_options: &GameRuleOptions) {
        let year = year_from_game_id(game_id);
        let era: Era = year.into();
        process_game_run_expectancy_by_inning(game_id, final_game_situation, situations,
            game_rule_options,
             |inning, runs_gained, mut process_fn| process_fn(self.stats.entry((inning, era)).or_default(), runs_gained));
    }

    fn merge_into_impl(self: &Self, other: &mut dyn Any) { 
        let other = other.downcast_mut::<Self>().unwrap();
        for entry in self.stats.iter() {
            let other_entry = other.stats.entry(*entry.0).or_default();
            if other_entry.len() < entry.1.len() {
                other_entry.resize(entry.1.len(), 0);
            }
            for i in 0..entry.1.len() {
                other_entry[i] += entry.1[i];
            }
        }
    }

    fn name_impl(&self) -> &'static str { "StatsRunExpectancyPerInningByInningAndEraReport" }
    fn make_new_impl(&self) -> Box<dyn Report> { Box::new(Self::new()) }
    fn get_stats<'a>(&'a self) -> &'a HashMap<Self::Key, Self::Value> { &self.stats }
    fn write_key<T:Write>(&self, file: &mut T, key: &Self::Key) {
        write!(file, "({}, {}), {}", key.0.number, key.0.is_home, key.1).unwrap();
    }
    fn write_value<T:Write>(&self, file: &mut T, value: &Self::Value) {
        write!(file, "{}", format_vec_default(value)).unwrap();
    }
    fn write_extra<T:Write>(&self, file: &mut T, _key: &Self::Key, value: &Self::Value) {
        write_extra_run_expectancy_by_inning_info(file, value);
    }

    fn report_file_name() -> &'static str { "analysis/runsByInning/runsperinningbyinninganderastats" }
}
fn format_vec_default<T:Display>(runs_vec: &[T]) -> String {
    return format_vec(runs_vec, |val| val.to_string());
}
fn format_vec<T,F>(runs_vec: &[T], formatter: F) -> String
    where F: Fn(&T) -> String {
    // https://stackoverflow.com/a/30325430/118417
    let mut comma_separated = "[".to_owned();

    if runs_vec.len() > 0 {
        for num in &runs_vec[..runs_vec.len() - 1] {
            comma_separated.push_str(&formatter(&num));
            comma_separated.push_str(", ");
        }
        comma_separated.push_str(&formatter(&(runs_vec.last().unwrap())));
    }
    comma_separated.push_str("]");
    comma_separated
}
