#[macro_use] extern crate lazy_static;
extern crate regex;
use std::{collections::HashSet, convert::TryInto};
use anyhow::{anyhow, Result};

//TODO - remove this
#[allow(unused_imports)]
//TODO - remove this
#[allow(dead_code)]

use data::{RunnerDests, RunnerFinalPosition, RunnerInitialPosition};
use regex::Regex;

mod data {
    //TODO - remove this
    #![allow(dead_code)]
    use std::{collections::HashMap, convert::TryFrom};
    use anyhow::anyhow;

    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
    pub enum RunnerInitialPosition {
        Batter,
        FirstBase,
        SecondBase,
        ThirdBase
    }

    impl TryFrom<char> for RunnerInitialPosition {
        type Error = anyhow::Error;

        fn try_from(value: char) -> Result<Self, Self::Error> {
            match value {
                'B' => Ok(RunnerInitialPosition::Batter),
                '1' => Ok(RunnerInitialPosition::FirstBase),
                '2' => Ok(RunnerInitialPosition::SecondBase),
                '3' => Ok(RunnerInitialPosition::ThirdBase),
                _ => Err(anyhow!("Unrecognized char for RunnerInitialPosition"))
            }
        }
    }

    impl RunnerInitialPosition {
        pub fn base_number(self: &Self) -> usize {
            match *self {
                RunnerInitialPosition::Batter => 0,
                RunnerInitialPosition::FirstBase => 1,
                RunnerInitialPosition::SecondBase => 2,
                RunnerInitialPosition::ThirdBase => 3
            }
        }

        pub fn runner_index(self: &Self) -> usize {
            match *self {
                RunnerInitialPosition::Batter => panic!("Can't call runner_index() on Batter"),
                RunnerInitialPosition::FirstBase => 0,
                RunnerInitialPosition::SecondBase => 1,
                RunnerInitialPosition::ThirdBase => 2
            }
        }
    }

    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    pub enum RunnerFinalPosition {
        FirstBase,
        SecondBase,
        ThirdBase,
        HomePlate, // this means the runner scored
        StillAtBat, // only valid for Batter
        Undetermined,
        Out
    }

    impl TryFrom<char> for RunnerFinalPosition {
        type Error = anyhow::Error;

        fn try_from(value: char) -> Result<Self, Self::Error> {
            match value {
                '1' => Ok(RunnerFinalPosition::FirstBase),
                '2' => Ok(RunnerFinalPosition::SecondBase),
                '3' => Ok(RunnerFinalPosition::ThirdBase),
                'H' => Ok(RunnerFinalPosition::HomePlate),
                _ => Err(anyhow!("Unrecognized char for RunnerFinalPosition"))
            }
        }
    }



    impl RunnerFinalPosition {
        pub fn runner_index(self: &Self) -> usize {
            match *self {
                RunnerFinalPosition::FirstBase => {
                    0
                },
                RunnerFinalPosition::SecondBase => {
                    1
                },
                RunnerFinalPosition::ThirdBase => {
                    2
                },
                _ => {
                    //TODO
                    panic!("runner_index() called on {:?}", self);
                }
            }
        }
        pub fn base_number(self: &Self) -> usize {
            match *self {
                RunnerFinalPosition::FirstBase => {
                    1
                },
                RunnerFinalPosition::SecondBase => {
                    2
                },
                RunnerFinalPosition::ThirdBase => {
                    3
                },
                RunnerFinalPosition::HomePlate => {
                    4
                },
                _ => {
                    //TODO
                    panic!("base_number() called on {:?}", self);
                }
            }

        }
    }

    pub struct RunnerDests {
        // Putting this struct in a module so its implementation is hidden.
        // TODO - Probably want to move this to a simple array with 4 entries
        dests: HashMap<RunnerInitialPosition, RunnerFinalPosition>
    }

    impl RunnerDests {
        pub fn new_from_runners(runners: &[bool;3]) -> RunnerDests {
            let mut dests = HashMap::new();
            if runners[0] {
                // TODO - this is a change from python, used to be StillAtBat (-1)
                dests.insert(RunnerInitialPosition::FirstBase, RunnerFinalPosition::Undetermined);
            }
            if runners[1] {
                // TODO - this is a change from python, used to be StillAtBat (-1)
                dests.insert(RunnerInitialPosition::SecondBase, RunnerFinalPosition::Undetermined);
            }
            if runners[2] {
                // TODO - this is a change from python, used to be StillAtBat (-1)
                dests.insert(RunnerInitialPosition::ThirdBase, RunnerFinalPosition::Undetermined);
            }
            dests.insert(RunnerInitialPosition::Batter, RunnerFinalPosition::Undetermined);
            RunnerDests { dests }
        }

        pub fn batter_to_first(self: &mut Self) {
            self.dests.insert(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase);
            if let Some(entry) = self.dests.get_mut(&RunnerInitialPosition::FirstBase) {
                *entry = RunnerFinalPosition::SecondBase;
                if let Some(entry) = self.dests.get_mut(&RunnerInitialPosition::SecondBase) {
                    *entry = RunnerFinalPosition::ThirdBase;
                    if let Some(entry) = self.dests.get_mut(&RunnerInitialPosition::ThirdBase) {
                        *entry = RunnerFinalPosition::HomePlate;
                    }
                }
                else {
                    if let Some(entry) = self.dests.get_mut(&RunnerInitialPosition::ThirdBase) {
                        *entry = RunnerFinalPosition::ThirdBase;
                    }
                }
            }
            else {
                if let Some(entry) = self.dests.get_mut(&RunnerInitialPosition::SecondBase) {
                    *entry = RunnerFinalPosition::SecondBase;
                }
                if let Some(entry) = self.dests.get_mut(&RunnerInitialPosition::ThirdBase) {
                    *entry = RunnerFinalPosition::ThirdBase;
                }
            }
        }

        pub fn len(self: &Self) -> usize {
            self.dests.len()
        }

        pub fn get(self: &Self, key: RunnerInitialPosition) -> Option<RunnerFinalPosition> {
            self.dests.get(&key).map(|x| *x)
        }

        pub fn keys(self: &Self) -> impl Iterator<Item=RunnerInitialPosition> + '_ {
            self.dests.keys().map(|x| *x).into_iter()
        }

        pub fn set_all<F>(self: &mut Self, func: F)
            where F: Fn(RunnerInitialPosition) -> RunnerFinalPosition {
            //self.dests.entry(key)
            for (&key, value) in self.dests.iter_mut() {
                *value = func(key);
            }
        }

        pub fn set(self: &mut Self, key: RunnerInitialPosition, value: RunnerFinalPosition) {
            self.dests.insert(key, value);
        }
    }

}

//TODO - remove this
#[allow(dead_code)]
#[derive(Clone, Copy, Debug)]
enum Verbosity {
    Quiet = 0,
    Normal = 1,
    Verbose = 2
}

impl Verbosity {
    fn is_at_least(self: &Self, compare: Verbosity) -> bool {
        return *self as u8 >= compare as u8;
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
struct GameSituation {
    // Whether runners are on first, second, third bases
    runners: [bool;3],
    inning: u8,
    cur_score_diff: i8,
    outs: u8, // TODO - should this be an enum?
    is_home: bool,
}

impl GameSituation {
    //TODO - remove this
    #![allow(dead_code)]

    fn new() -> GameSituation {
        GameSituation {
            cur_score_diff: 0,
            inning: 1,
            is_home: false,
            outs: 0,
            runners: [false, false, false]
        }
    }

    // Advances to the next inning if there are 3 outs
    fn next_inning_if_three_outs(self: &mut Self) {
        if self.outs >= 3 {
            if self.is_home {
                self.is_home = false;
                self.inning += 1;
            }
            else {
                self.is_home = true;
            }
            self.outs = 0;
            self.runners[0] = false;
            self.runners[1] = false;
            self.runners[2] = false;
            self.cur_score_diff = -1 * self.cur_score_diff;
        }
    }

    // Whether the home team won, or None if it's still tied
    fn is_home_winning(self: &Self) -> Option<bool> {
        if self.cur_score_diff == 0 {
            // This game must have been tied when it stopped.
            None
        }
        else {
            if self.is_home {
                Some(self.cur_score_diff > 0)
            }
            else {
                Some(self.cur_score_diff < 0)
            }
        }
    }

    pub fn parse_play(self: &mut GameSituation, line: &str, verbosity: Verbosity) -> Result<()> {
        // decription of the format is at http://www.retrosheet.org/eventfile.htm
        let play_line_info = PlayLineInfo::new_from_line(line);
        let mut runner_dests = RunnerDests::new_from_runners(&self.runners);
        // TODO perf - use a Vec<> or something? Or do we even need this, can we just use runner_dests?
        let beginning_runners = runner_dests.keys().collect::<HashSet<_>>();
        let mut runners_default_stay_still = false;
        //TODO - verbosity log statements
        if verbosity.is_at_least(Verbosity::Verbose) {
            println!("Game situation is {:?}", self);
            println!("{}", line);
        }

        if self.inning != play_line_info.inning {
            return Err(anyhow!("Mismatched inning - expected {} from GameSituation, got {} from play_line_info", self.inning, play_line_info.inning));
        }
        if self.is_home != play_line_info.is_home {
            return Err(anyhow!("Mismatched is_home - expected {} from GameSituation, got {} from play_line_info", self.is_home, play_line_info.is_home));
        }

        let play_string = &play_line_info.play_str;
        // TODO perf - is this collect() necessary?
        let play_array: Vec<&str> = play_string.split('.').collect();
        if play_array.len() > 2 {
            return Err(anyhow!("play_array is too long after splitting on '.': \"{}\"", play_string));
        }
        // Deal with the first part of the string.
        let batter_events = play_array[0].split(';');
        for batter_event in batter_events {
            let batter_event = batter_event.trim();
            let mut done_parsing_event = false;
            lazy_static! {
                static ref SIMPLE_HIT_RE : Regex = Regex::new(r"^([SDTH])(?:\d|/)").unwrap();
                static ref SIMPLE_HIT_2_RE : Regex = Regex::new(r"^([SDTH])\s*$").unwrap();
            }
            let simple_hit_match = SIMPLE_HIT_RE.captures(batter_event);
            let simple_hit_2_match = SIMPLE_HIT_RE.captures(batter_event);
            let captures = simple_hit_match.or(simple_hit_2_match);
            if let Some(inner_captures) = captures {
                let type_of_hit = inner_captures.get(1).unwrap().as_str();
                match type_of_hit {
                    "S" => {
                        runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase);
                    },
                    "D" => {
                        runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::SecondBase);
                    },
                    "T" => {
                        runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::ThirdBase);
                    },
                    "H" => {
                        runner_dests.set_all(|_| RunnerFinalPosition::HomePlate);
                    },
                    _ => return Err(anyhow!(format!("Unexpected type_of_hit {}", type_of_hit)))
                }
                // Sometimes these aren't specified - assume runners don't move
                runners_default_stay_still = true;
                done_parsing_event = true;
            }
            if !done_parsing_event {
                if batter_event.starts_with("HR") {
                    runner_dests.set_all(|_| RunnerFinalPosition::HomePlate);
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("K") {
                    runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::Out);
                    runners_default_stay_still = true;
                    if batter_event.starts_with("K+") || batter_event.starts_with("K23+") {
                        let temp_event = if batter_event.starts_with("K+") { &batter_event[2..] } else { &batter_event[4..] };
                        if temp_event.starts_with("SB") {
                            GameSituation::handle_sb_event(temp_event, &mut runner_dests)?;
                        }
                        else if temp_event.starts_with("CS") || temp_event.starts_with("POCS"){
                            GameSituation::handle_cs_or_pocs_event(temp_event, &mut runner_dests)?;
                        }
                        else if temp_event.starts_with("PO") {
                            GameSituation::handle_po_event(temp_event, &mut runner_dests)?;
                        }
                        //TODO - pretty sure this isn't tested
                        else if temp_event.starts_with("PB") || temp_event.starts_with("WP") {
                            // nothing happens
                        }
                        else if temp_event.starts_with("OA") || temp_event.starts_with("OBA") || temp_event.starts_with("DI") {
                            // nothing happens
                        }
                        else if temp_event.starts_with("E") {
                            // nothing happens
                        }
                        else {
                            if verbosity.is_at_least(Verbosity::Normal) {
                                println!("ERROR - unrecognized K+ event {}", temp_event);
                            }
                            return Err(anyhow!("ERROR - unrecognized K+ event {}", temp_event));
                        }
                    }
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("NP") {
                    // No play
                    runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::StillAtBat);
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("PB") || batter_event.starts_with("WP") {
                    // Passed ball or wild pitch
                    runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::StillAtBat);
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                // Note that we already checked for "WP"
                if batter_event.starts_with("W") || batter_event.starts_with("I") {
                    // walk
                    runner_dests.batter_to_first();
                    if batter_event.starts_with("W+") || batter_event.starts_with("IW+") || batter_event.starts_with("I+") {
                        let temp_event = if batter_event.starts_with("IW+") { &batter_event[3..] } else { &batter_event[2..] };
                        if temp_event.starts_with("SB") {
                            GameSituation::handle_sb_event(temp_event, &mut runner_dests)?;
                        }
                        else if temp_event.starts_with("CS") || temp_event.starts_with("POCS"){
                            GameSituation::handle_cs_or_pocs_event(temp_event, &mut runner_dests)?;
                        }
                        else if temp_event.starts_with("PO") {
                            GameSituation::handle_po_event(temp_event, &mut runner_dests)?;
                        }
                        else if temp_event.starts_with("PB") || temp_event.starts_with("WP") {
                            // passed ball or wild pitch
                        }
                        else if temp_event.starts_with("OA") || temp_event.starts_with("DI") {
                            // other advance or defensive indifference
                        }
                        else if temp_event.starts_with("E") {
                            // already had a walk, so whatever the error is will be shown in the runners
                        }
                        else {
                            if verbosity.is_at_least(Verbosity::Normal) {
                                println!("ERROR - unrecognized W+ event {}", temp_event);
                            }
                            return Err(anyhow!("ERROR - unrecognized W+ event {}", temp_event));
                        }
                    }
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("HP") {
                    // hit by pitch
                    runner_dests.batter_to_first();
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("DGR") {
                    // ground rule double
                    runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::SecondBase);
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("C/") || batter_event == "C" {
                    // catcher's interference
                    runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase);
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }



            // TODO - much more
            if !done_parsing_event {
                return Err(anyhow!("ERROR - unrecognized event {} (line is {})", batter_event, line));
            }
        }

        // TODO - Now parse runner stuff
        if play_array.len() > 1 {
            let runner_array = play_array[1].split(';').into_iter().map(|x| x.trim());
            for runner_item in runner_array {
                let runner_chars = runner_item.chars().collect::<Vec<_>>();
                if runner_chars.len() != 3 {
                    if '(' != runner_chars[3] {
                        return Err(anyhow!("Expected '(' as fourth character in runner_chars \"{}\"", runner_item));
                    }
                }
                let initial_runner: RunnerInitialPosition = runner_chars[0].try_into()?;
                let final_runner: RunnerFinalPosition = runner_chars[2].try_into()?;
                match runner_chars[1] {
                    '-' => {
                        // This looks weird, but sometimes a runner can go to the
                        // same base (a little redundant, but OK)
                        //TODO refactor
                        if initial_runner.base_number() > final_runner.base_number() {
                            return Err(anyhow!(format!("Runner went backwards from {:?} to {:?} for play {}", initial_runner, final_runner, play_string)));
                        }
                        runner_dests.set(initial_runner, final_runner);
                    },
                    'X' => {
                        //TODO
                    },
                    _ => return Err(anyhow!(format!("Invalid character {} in runner specification for play {}", runner_chars[1], play_string)))
                };
            }
        }

        // TODO even more stuff

        // Deal with runner_dests
        // TODO - move this into a method
        self.runners = [false, false, false];
        let mut undetermined_runner = None;
        for key in runner_dests.keys() {
            // TODO - do this a more performant way?
            if beginning_runners.get(&key).is_none() {
                return Err(anyhow!("ERROR - picked up extra runner {:?}", key));
            }
            let dest = runner_dests.get(key).unwrap();
            match dest {
                RunnerFinalPosition::Out => {
                    self.outs += 1;
                },
                RunnerFinalPosition::HomePlate => {
                    self.cur_score_diff += 1;
                },
                RunnerFinalPosition::Undetermined => {
                    if runners_default_stay_still {
                        if *self.runners.get(key.runner_index()).unwrap() {
                            if verbosity.is_at_least(Verbosity::Normal) {
                                println!("ERROR - already a runner at base {}!", key.runner_index());
                            }
                            return Err(anyhow!("ERROR - duplicate runner at base {}", key.runner_index()));
                        }
                        *(self.runners.get_mut(key.runner_index()).unwrap()) = true;
                    }
                    else {
                        undetermined_runner = Some(key);
                    }
                },
                RunnerFinalPosition::StillAtBat => {
                    if key != RunnerInitialPosition::Batter {
                        return Err(anyhow!("Got StillAtBat for initial position {:?}", key));
                    }
                },
                RunnerFinalPosition::FirstBase | RunnerFinalPosition::SecondBase | RunnerFinalPosition::ThirdBase => {
                    if *self.runners.get(dest.runner_index()).unwrap() {
                        if verbosity.is_at_least(Verbosity::Normal) {
                            println!("ERROR - already a runner at base {}!", dest.runner_index());
                        }
                        return Err(anyhow!("ERROR - duplicate runner at base {}", dest.runner_index()));
                    }
                    *(self.runners.get_mut(dest.runner_index()).unwrap()) = true;
                }
            }
        }
        if undetermined_runner.is_some() && self.outs < 3 {
            return Err(anyhow!("Got undetermined runner {:?} with less than three outs!", undetermined_runner))
        }
        self.next_inning_if_three_outs();
        Ok(())
    }

    fn handle_sb_event(sb_event: &str, runner_dests: &mut RunnerDests) -> Result<()> {
        assert!(sb_event.starts_with("SB"));
        let sb_parts = sb_event.split(';');
        for sb_part in sb_parts {
            let dest: RunnerFinalPosition = sb_part.chars().nth(2)
                .ok_or(anyhow!("SB part too short: {}", sb_event))?.try_into()?;
            if dest == RunnerFinalPosition::FirstBase {
                return Err(anyhow!("SB to first base?: {}", sb_event));
            }
            let start: RunnerInitialPosition = (dest.base_number() - 1).to_string().chars().next().unwrap().try_into()?;
            runner_dests.set(start, dest);
        }
        Ok(())
    }

    fn handle_cs_or_pocs_event(cs_event: &str, runner_dests: &mut RunnerDests) -> Result<()> {
        assert!(cs_event.starts_with("CS") || cs_event.starts_with("POCS"));
        lazy_static! {
            static ref CS_ERROR_RE : Regex = Regex::new(r"^(?:PO)?CS.\([^)]*?E.*?\)").unwrap();
        }
        let dest_position = if cs_event.starts_with("CS") { 2 } else { 4 };
        let dest: RunnerFinalPosition = cs_event.chars().nth(dest_position)
            .ok_or(anyhow!("CS line too short {}", cs_event))?.try_into()?;
        if dest == RunnerFinalPosition::FirstBase {
            return Err(anyhow!("CS to first base?: {}", cs_event));
        }
        let start: RunnerInitialPosition = (dest.base_number() - 1).to_string().chars().next().unwrap().try_into()?;

        if CS_ERROR_RE.is_match(cs_event) {
            // Error, so no out.
            runner_dests.set(start, dest);
        }
        else {
            runner_dests.set(start, RunnerFinalPosition::Out);
        }
        Ok(())
    }

    fn handle_po_event(po_event: &str, runner_dests: &mut RunnerDests) -> Result<()> {
        assert!(po_event.starts_with("PO"));
        lazy_static! {
            static ref PO_ERROR_RE : Regex = Regex::new(r"^PO.\([^)]*?E.*?\)").unwrap();
        }
        if PO_ERROR_RE.is_match(po_event) {
            // Error, so no out
        }
        else {
            let start: RunnerInitialPosition = po_event.chars().nth(2)
                .ok_or(anyhow!("PO line too short: {}", po_event))?.try_into()?;
            if start == RunnerInitialPosition::Batter {
                return Err(anyhow!("PO for batter?: {}", po_event));
            }
            runner_dests.set(start, RunnerFinalPosition::Out);
        }
        Ok(())
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
struct PlayLineInfo<'a> {
    inning: u8,
    is_home: bool,
    player_id: &'a str,
    count_when_play_happened: &'a str,
    pitches_str: &'a str,
    play_str: String
}

impl PlayLineInfo<'_> {
    fn new_from_line<'a>(line: &'a str) -> PlayLineInfo<'a> {
        lazy_static! {
            // TODO perf - opt out of unicode?
            static ref PLAY_RE : Regex = Regex::new(r"^play,\s?(\d+),\s?([01]),(.*?),(.*?),(.*?),(.*)$").unwrap();
        }
        let play_match = PLAY_RE.captures(line).unwrap();
        // remove characters we don't care about
        let play_str = play_match.get(6).unwrap().as_str().chars()
            .filter(|&x| x != '!' && x != '#' && x != '?').collect();
        return PlayLineInfo {
            inning: play_match.get(1).unwrap().as_str().parse::<u8>().unwrap(),
            is_home: play_match.get(2).unwrap().as_str() == "1",
            player_id: play_match.get(3).unwrap().as_str(),
            count_when_play_happened: play_match.get(4).unwrap().as_str(),
            pitches_str: play_match.get(5).unwrap().as_str(),
            play_str: play_str
        }
    }
}


// TODO - parallel

fn main() {
    println!("Hello, world!");
}

#[cfg(test)]
mod tests {
    #![allow(non_snake_case)]
    use std::collections::HashMap;
    use data::*;
    use super::*;

    #[test]
    fn test_next_inning_if_three_outs__zero_outs() {
        let orig_inning = GameSituation {
            cur_score_diff: 2,
            inning: 1,
            is_home: false,
            outs: 0,
            runners: [false, true, false]
        };
        let mut new_inning = orig_inning.clone();
        new_inning.next_inning_if_three_outs();
        assert_eq!(orig_inning, new_inning);
    }

    #[test]
    fn test_next_inning_if_three_outs__one_out() {
        let orig_inning = GameSituation {
            cur_score_diff: 2,
            inning: 1,
            is_home: false,
            outs: 1,
            runners: [false, true, false]
        };
        let mut new_inning = orig_inning.clone();
        new_inning.next_inning_if_three_outs();
        assert_eq!(orig_inning, new_inning);
    }

    #[test]
    fn test_next_inning_if_three_outs__two_outs() {
        let orig_inning = GameSituation {
            cur_score_diff: 2,
            inning: 1,
            is_home: false,
            outs: 2,
            runners: [false, true, false]
        };
        let mut new_inning = orig_inning.clone();
        new_inning.next_inning_if_three_outs();
        assert_eq!(orig_inning, new_inning);
    }

    #[test]
    fn test_next_inning_if_three_outs__three_outs_home() {
        let mut orig_inning = GameSituation {
            cur_score_diff: 2,
            inning: 1,
            is_home: true,
            outs: 3,
            runners: [false, true, false]
        };
        orig_inning.next_inning_if_three_outs();
        assert_eq!(GameSituation {
            cur_score_diff: -2,
            inning: 2,
            is_home: false,
            outs: 0,
            runners: [false, false, false]
        }, orig_inning);
    }

    #[test]
    fn test_next_inning_if_three_outs__three_outs_visitor() {
        let mut orig_inning = GameSituation {
            cur_score_diff: 2,
            inning: 1,
            is_home: false,
            outs: 3,
            runners: [false, true, false]
        };
        orig_inning.next_inning_if_three_outs();
        assert_eq!(GameSituation {
            cur_score_diff: -2,
            inning: 1,
            is_home: true,
            outs: 0,
            runners: [false, false, false]
        }, orig_inning);
    }

    #[test]
    fn test_is_home_winning__home_inning_tied() {
        let mut game = GameSituation::new();
        game.is_home = true;
        game.cur_score_diff = 0;
        assert_eq!(None, game.is_home_winning());
    }

    #[test]
    fn test_is_home_winning__visitor_inning_tied() {
        let mut game = GameSituation::new();
        game.is_home = false;
        game.cur_score_diff = 0;
        assert_eq!(None, game.is_home_winning());
    }

    #[test]
    fn test_is_home_winning__home_inning_home_ahead() {
        let mut game = GameSituation::new();
        game.is_home = true;
        game.cur_score_diff = 2;
        assert_eq!(Some(true), game.is_home_winning());
    }

    #[test]
    fn test_is_home_winning__home_inning_visitor_ahead() {
        let mut game = GameSituation::new();
        game.is_home = true;
        game.cur_score_diff = -2;
        assert_eq!(Some(false), game.is_home_winning());
    }

    #[test]
    fn test_is_home_winning__visitor_inning_home_ahead() {
        let mut game = GameSituation::new();
        game.is_home = false;
        game.cur_score_diff = -2;
        assert_eq!(Some(true), game.is_home_winning());
    }

    #[test]
    fn test_is_home_winning__visitor_inning_visitor_ahead() {
        let mut game = GameSituation::new();
        game.is_home = false;
        game.cur_score_diff = 2;
        assert_eq!(Some(false), game.is_home_winning());
    }

    #[test]
    fn test_batter_to_first() {
        // Yikes, this type is something
        let data: Vec<([bool;3], Box<dyn Iterator<Item=&(RunnerInitialPosition, RunnerFinalPosition)>>)> = vec![
            ([false, false, false],
             Box::new([(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase)].iter())),
            ([true, false, false],
             Box::new([(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase),
                       (RunnerInitialPosition::FirstBase, RunnerFinalPosition::SecondBase)].iter())),
            ([false, true, false],
             Box::new([(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase),
                       (RunnerInitialPosition::SecondBase, RunnerFinalPosition::SecondBase)].iter())),
            ([true, true, false],
             Box::new([(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase),
                       (RunnerInitialPosition::FirstBase, RunnerFinalPosition::SecondBase),
                       (RunnerInitialPosition::SecondBase, RunnerFinalPosition::ThirdBase)].iter())),
            ([false, false, true],
             Box::new([(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase),
                       (RunnerInitialPosition::ThirdBase, RunnerFinalPosition::ThirdBase)].iter())),
            ([true, false, true],
             Box::new([(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase),
                       (RunnerInitialPosition::FirstBase, RunnerFinalPosition::SecondBase),
                       (RunnerInitialPosition::ThirdBase, RunnerFinalPosition::ThirdBase)].iter())),
            ([false, true, true],
             Box::new([(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase),
                       (RunnerInitialPosition::SecondBase, RunnerFinalPosition::SecondBase),
                       (RunnerInitialPosition::ThirdBase, RunnerFinalPosition::ThirdBase)].iter())),
            ([true, true, true],
             Box::new([(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase),
                       (RunnerInitialPosition::FirstBase, RunnerFinalPosition::SecondBase),
                       (RunnerInitialPosition::SecondBase, RunnerFinalPosition::ThirdBase),
                       (RunnerInitialPosition::ThirdBase, RunnerFinalPosition::HomePlate)].iter()))
        ];
        for (runners, expectedIter) in data {
            let mut dests = RunnerDests::new_from_runners(&runners);
            dests.batter_to_first();
            let expected = expectedIter.map(|x| *x).collect::<HashMap<_,_>>();
            assert_eq!(expected.len(), dests.len(), "{:?}", runners);
            for (key, expectedValue) in expected {
                assert_eq!(Some(expectedValue), dests.get(key), "{:?} {:?}", runners, key);
            }
        }
    }

    #[test]
    fn test_parse_play_line_info() {
        let play_line_info_str = "play,4,1,corrc001,22,BSBFFX,HR/78/F";
        let play_line_info = PlayLineInfo::new_from_line(play_line_info_str);
        let expected = PlayLineInfo {
            inning: 4,
            is_home: true,
            player_id: "corrc001",
            count_when_play_happened: "22",
            pitches_str: "BSBFFX",
            play_str: "HR/78/F".to_owned()
        };
        assert_eq!(expected, play_line_info);
    }

    #[test]
    fn test_verbosity_is_at_least() {
        assert_eq!(true, Verbosity::Verbose.is_at_least(Verbosity::Verbose));
        assert_eq!(true, Verbosity::Verbose.is_at_least(Verbosity::Normal));
        assert_eq!(true, Verbosity::Verbose.is_at_least(Verbosity::Quiet));
        assert_eq!(false, Verbosity::Normal.is_at_least(Verbosity::Verbose));
        assert_eq!(true, Verbosity::Normal.is_at_least(Verbosity::Normal));
        assert_eq!(true, Verbosity::Normal.is_at_least(Verbosity::Quiet));
        assert_eq!(false, Verbosity::Quiet.is_at_least(Verbosity::Verbose));
        assert_eq!(false, Verbosity::Quiet.is_at_least(Verbosity::Normal));
        assert_eq!(true, Verbosity::Quiet.is_at_least(Verbosity::Quiet));
    }

    mod parse_play_tests {
        #![allow(non_snake_case)]
        use super::*;

        fn setup_with_inning(outs: u8, is_home: bool, runners: [bool;3], play_string: &str) -> (GameSituation, String) {
            let situation = GameSituation {
                runners,
                inning: 1,
                cur_score_diff: 0,
                outs,
                is_home
            };

            (situation, format!("play,1,{},,,,{}", if situation.is_home { 1 } else { 0 }, play_string))
        }

        fn setup(runners: [bool;3], play_string: &str) -> (GameSituation, String) {
            let situation = GameSituation {
                runners,
                inning: 1,
                cur_score_diff: 0,
                outs: 0,
                is_home: false
            };

            (situation, format!("play,1,{},,,,{}", if situation.is_home { 1 } else { 0 }, play_string))
        }

        fn assert_result(expected_situation: &GameSituation, initial_situation: &mut GameSituation, play_line: &str) -> Result<()> {
            initial_situation.parse_play(&play_line, Verbosity::Normal)?;
            assert_eq!(expected_situation, initial_situation);
            Ok(())
        }

        #[test]
        #[ignore]
        fn test_simpleout() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "8");
            let mut expected_situation = situation.clone();
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_catchers_interference() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "C/E2");
            let mut expected_situation = situation.clone();
            expected_situation.runners[0] = true;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_catchers_interference_runner() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "C/E2.1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, true, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_catchers_interference_runner_explicit() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "C/E2.B-1;1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, true, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_pitchers_interference() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "C/E1");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_first_basemans_interference() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "C/E3");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_single() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "S7");
            let mut expected_situation = situation.clone();
            expected_situation.runners[0] = true;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_double() -> Result<()> {
            let (mut situation, play_line) = setup([true, true, true], "D7/G5.3-H;2-H;1-H");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            expected_situation.cur_score_diff = 3;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_triple() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "T9/F9LD.2-H");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, true];
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_ground_rule_double() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "DGR/L9LS.2-H");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_home_run() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "H/L7D");
            let mut expected_situation = situation.clone();
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_home_run_explicit_runners() -> Result<()> {
            let (mut situation, play_line) = setup([true, true, false], "HR/F78XD.2-H;1-H");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.cur_score_diff = 3;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_home_run_inside_park() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, true], "HR9/F9LS.3-H;1-H");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.cur_score_diff = 3;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_home_run_inside_park_just_h() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, true], "H9/F9LS.3-H;1-H");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.cur_score_diff = 3;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_home_run_inside_park_just_h_no_runners() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "H9/F9LS");
            let mut expected_situation = situation.clone();
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_hit_by_pitch() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "HP.1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, true, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_hit_by_pitch_no_runners() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "HP");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_strikeout() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "K");
            let mut expected_situation = situation.clone();
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_strikeout_putout() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "K23");
            let mut expected_situation = situation.clone();
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_strikeout_passed_ball() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "K+PB.1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_strikeout_miscue() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, true], "K+WP.B-1");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, true];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_strikeout_putout_other_runner_advance() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "K23+WP.2-3");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, true];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_strikeout_putout_caught_stealing() -> Result<()> {
            // see game BAL196505282, end of 5th inning
            let (mut situation, play_line) = setup([false, true, false], "K23+CS3(34)/DP");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 2;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_strikeout_pickoff_other_runner_advance() -> Result<()> {
            let (mut situation, play_line) = setup([true, true, false], "K+PO1.2-3");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, true];
            expected_situation.outs = 2;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_strikeout_pickoff_error() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "K+PO2(E3).2-3");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, true];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_wild_pitch() -> Result<()> {
            let (mut situation, play_line) = setup([true, true, false], "WP.2-3;1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, true];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_passed_ball() -> Result<()> {
            let (mut situation, play_line) = setup([true, true, false], "PB.2-3");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, true];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_no_play() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "NP");
            let expected_situation = situation.clone();
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_walk() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "W.1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, true, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_intentional_walk() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, true], "IW");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, true];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_walk_wild_pitch() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "W+WP.2-3");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, true];
            assert_result(&expected_situation, &mut situation, &play_line)
        }


        #[test]
        fn test_walk_plus_putout_caught_stealing() -> Result<()> {
            // game CHN201708160, bottom of the 4th
            let (mut situation, play_line) = setup([false, true, false], "W+POCS3(26)");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, false];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }
    }
}