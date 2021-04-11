mod reports;

#[macro_use] extern crate lazy_static;
extern crate regex;
extern crate encoding;
use std::{any::Any, collections::HashMap, collections::HashSet, convert::TryInto, fmt::{Debug, Display}, fs::File, io::{self, BufRead}, io::{BufWriter, Write}, path::{Path, PathBuf}};
use anyhow::{anyhow, Result};
use argh::FromArgs;
use data::{RunnerDests, RunnerFinalPosition, RunnerInitialPosition};
use regex::{Regex, RegexBuilder};
use glob::glob;
use encoding::{Encoding, DecoderTrap};
use encoding::all::ISO_8859_1;
use smallvec::{smallvec, SmallVec};
use smol_str::SmolStr;
use rayon::prelude::*;


mod data {
    use std::{convert::{TryFrom, TryInto}};
    use anyhow::anyhow;

    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
    pub enum RunnerInitialPosition {
        Batter = 0,
        FirstBase = 1,
        SecondBase = 2,
        ThirdBase = 3
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

    impl TryFrom<u8> for RunnerInitialPosition {
        type Error = anyhow::Error;

        fn try_from(value: u8) -> Result<Self, Self::Error> {
            match value {
                0..=3 => Ok(unsafe { std::mem::transmute(value as u8)}),
                _ => Err(anyhow!("invalid RunnerInitialPosition value"))
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

        pub fn runner_index(self: &Self) -> anyhow::Result<usize> {
            match *self {
                RunnerInitialPosition::Batter => Err(anyhow!("Can't call runner_index() on Batter")),
                RunnerInitialPosition::FirstBase => Ok(0),
                RunnerInitialPosition::SecondBase => Ok(1),
                RunnerInitialPosition::ThirdBase => Ok(2)
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
        pub fn runner_index(self: &Self) -> anyhow::Result<usize> {
            match *self {
                RunnerFinalPosition::FirstBase => Ok(0),
                RunnerFinalPosition::SecondBase => Ok(1),
                RunnerFinalPosition::ThirdBase => Ok(2),
                _ => Err(anyhow!("runner_index() called on {:?}", self))
            }
        }
        pub fn base_number(self: &Self) -> anyhow::Result<usize> {
            match *self {
                RunnerFinalPosition::FirstBase => Ok(1),
                RunnerFinalPosition::SecondBase => Ok(2),
                RunnerFinalPosition::ThirdBase => Ok(3),
                RunnerFinalPosition::HomePlate => Ok(4),
                _ => Err(anyhow!("base_number() called on {:?}", self))
            }
        }
        pub fn from_position(position: u8) -> Option<RunnerFinalPosition> {
            match position {
                3 => Some(RunnerFinalPosition::FirstBase),
                // second baseman and shortstop both map to second base
                4 | 6 => Some(RunnerFinalPosition::SecondBase),
                5 => Some(RunnerFinalPosition::ThirdBase),
                // I guess we don't need the catcher position here...
                _ => None
            }
        }
    }

    pub struct RunnerDests {
        // Putting this struct in a module so its implementation is hidden.
        dests: [Option<RunnerFinalPosition>;4],
    }

    impl RunnerDests {
        pub fn new_from_runners(runners: &[bool;3]) -> RunnerDests {
            let mut dests = [None, None, None, None];
            if runners[0] {
                dests[RunnerInitialPosition::FirstBase as usize] = Some(RunnerFinalPosition::Undetermined);
            }
            if runners[1] {
                dests[RunnerInitialPosition::SecondBase as usize] = Some(RunnerFinalPosition::Undetermined);
            }
            if runners[2] {
                dests[RunnerInitialPosition::ThirdBase as usize] = Some(RunnerFinalPosition::Undetermined);
            }
            dests[RunnerInitialPosition::Batter as usize] = Some(RunnerFinalPosition::Undetermined);
            RunnerDests { dests }
        }

        pub fn batter_to_first(self: &mut Self) {
            self.set(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase).unwrap();
            if self.dests[RunnerInitialPosition::FirstBase as usize] != None {
                self.dests[RunnerInitialPosition::FirstBase as usize] = Some(RunnerFinalPosition::SecondBase);
                if self.dests[RunnerInitialPosition::SecondBase as usize] != None {
                    self.dests[RunnerInitialPosition::SecondBase as usize] = Some(RunnerFinalPosition::ThirdBase);
                    if self.dests[RunnerInitialPosition::ThirdBase as usize] != None {
                        self.dests[RunnerInitialPosition::ThirdBase as usize] = Some(RunnerFinalPosition::HomePlate);
                    }
                }
                else {
                    if self.dests[RunnerInitialPosition::ThirdBase as usize] != None {
                        self.dests[RunnerInitialPosition::ThirdBase as usize] = Some(RunnerFinalPosition::ThirdBase);
                    }
                }
            }
            else {
                if self.dests[RunnerInitialPosition::SecondBase as usize] != None {
                    self.dests[RunnerInitialPosition::SecondBase as usize] = Some(RunnerFinalPosition::SecondBase);
                }
                if self.dests[RunnerInitialPosition::ThirdBase as usize] != None {
                    self.dests[RunnerInitialPosition::ThirdBase as usize] = Some(RunnerFinalPosition::ThirdBase);
                }
            }
        }

        pub fn set_batter_still_at_bat_if_not_set(self: &mut Self) {
            if self.dests[RunnerInitialPosition::Batter as usize] == Some(RunnerFinalPosition::Undetermined) {
                self.dests[RunnerInitialPosition::Batter as usize] = Some(RunnerFinalPosition::StillAtBat);
            }
        }

        pub fn get(self: &Self, key: RunnerInitialPosition) -> Option<RunnerFinalPosition> {
            self.dests[key as usize]
        }

        pub fn keys(self: &Self) -> impl Iterator<Item=RunnerInitialPosition> + '_ {
            let mut cur_position = 0;
            return std::iter::from_fn(move || {
                if cur_position == 4 {
                    return None;
                }
                while self.dests[cur_position].is_none() {
                    cur_position += 1;
                    if cur_position == 4 {
                        return None;
                    }
                }
                cur_position += 1;
                return Some((cur_position as u8 - 1).try_into().unwrap());
            });
        }

        pub fn set_all<F>(self: &mut Self, func: F)
            where F: Fn(RunnerInitialPosition) -> RunnerFinalPosition {
            for i in 0..4 {
                if self.dests[i].is_some() {
                    self.dests[i] = Some(func((i as u8).try_into().unwrap()));
                }
            }
        }

        pub fn set(self: &mut Self, key: RunnerInitialPosition, value: RunnerFinalPosition) -> anyhow::Result<()> {
            if self.dests[key as usize].is_none() {
                return Err(anyhow!("Added runner {:?}", key));
            }
            self.dests[key as usize] = Some(value);
            Ok(())
        }
    }
}

fn build_regex(s: &str) -> Regex {
    // PERF - This doesn't work, I guess we do need some Unicode for \w characters in Regexes?
    //RegexBuilder::new(s).unicode(false).build().unwrap()
    RegexBuilder::new(s).build().unwrap()
}

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

#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, PartialOrd, Ord)]
struct Inning {
    number: u8,
    is_home: bool,
}

impl Inning {
    fn new() -> Inning {
        Inning { number: 1, is_home: false }
    }
    fn next_inning(&self) -> Inning {
        if self.is_home {
            Inning { number: self.number + 1, is_home: false }
        }
        else {
            Inning { number: self.number, is_home: true }
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, PartialOrd, Ord)]
struct GameSituation {
    inning: Inning,
    outs: u8,
    // Whether runners are on first, second, third bases
    runners: [bool;3],
    cur_score_diff: i8,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, PartialOrd, Ord)]
struct GameRuleOptions {
    runner_starts_on_second_in_extra_innings: bool,
    innings: u8
}

#[derive(Clone, Copy, PartialEq, Eq, Debug, Hash, PartialOrd, Ord)]
struct BallsStrikes {
    balls: u8,
    strikes: u8
}
impl BallsStrikes {
    fn new() -> Self {
        Self {
            balls: 0,
            strikes: 0
        }
    }
    fn add_ball(&self) -> BallsStrikes {
        Self {
            balls: self.balls + 1,
            strikes: self.strikes
        }
    }
    fn add_strike(&self) -> BallsStrikes {
        Self {
            balls: self.balls,
            strikes: self.strikes + 1
        }
    }
}
impl Display for BallsStrikes {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_fmt(format_args!("{}-{}", self.balls, self.strikes))
    }
}

impl GameSituation {
    fn new() -> GameSituation {
        GameSituation {
            cur_score_diff: 0,
            inning: Inning::new(),
            outs: 0,
            runners: [false, false, false]
        }
    }

    // Advances to the next inning if there are 3 outs
    fn next_inning_if_three_outs(self: &mut Self, runner_starts_on_second_in_extra_innings: bool, innings: u8) {
        if self.outs >= 3 {
            self.inning = self.inning.next_inning();
            self.outs = 0;
            self.runners[0] = false;
            self.runners[1] = runner_starts_on_second_in_extra_innings && self.inning.number > innings;
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
            if self.inning.is_home {
                Some(self.cur_score_diff > 0)
            }
            else {
                Some(self.cur_score_diff < 0)
            }
        }
    }

    pub fn parse_play(self: &GameSituation, line: &str, game_rule_options: &GameRuleOptions) -> Result<GameSituation> {
        // decription of the format is at http://www.retrosheet.org/eventfile.htm
        let play_line_info = PlayLineInfo::from(line);
        let mut runner_dests = RunnerDests::new_from_runners(&self.runners);
        let mut runners_default_stay_still = false;
        let mut default_batter_base: Option<RunnerFinalPosition> = None;
        let mut out_at_bases: SmallVec<[RunnerFinalPosition;4]> = smallvec![];
        if get_verbosity().is_at_least(Verbosity::Verbose) {
            println!("Game situation is {:?}", self);
            println!("{}", line);
        }

        if self.inning != play_line_info.inning {
            return Err(anyhow!("Mismatched inning - expected {:?} from GameSituation, got {:?} from play_line_info", self.inning, play_line_info.inning));
        }

        let play_string = &play_line_info.play_str;
        let play_array: SmallVec<[&str;2]> = play_string.split('.').collect();
        if play_array.len() > 2 {
            return Err(anyhow!("play_array is too long after splitting on '.': \"{}\"", play_string));
        }
        // Deal with the first part of the string.
        let batter_events = play_array[0].split(';');
        for batter_event in batter_events {
            let batter_event = batter_event.trim();
            let mut done_parsing_event = false;
            lazy_static! {
                static ref SIMPLE_HIT_RE : Regex = build_regex(r"^([SDTH])(?:\d|/)");
                static ref SIMPLE_HIT_2_RE : Regex = build_regex(r"^([SDTH])\s*$");
            }
            let simple_hit_match = SIMPLE_HIT_RE.captures(batter_event);
            let simple_hit_2_match = SIMPLE_HIT_2_RE.captures(batter_event);
            let captures = simple_hit_match.or(simple_hit_2_match);
            if let Some(inner_captures) = captures {
                let type_of_hit = inner_captures.get(1).unwrap().as_str();
                match type_of_hit {
                    "S" => {
                        runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase).unwrap();
                    },
                    "D" => {
                        runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::SecondBase).unwrap();
                    },
                    "T" => {
                        runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::ThirdBase).unwrap();
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
                    runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::Out).unwrap();
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
                            if get_verbosity().is_at_least(Verbosity::Normal) {
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
                    runner_dests.set_batter_still_at_bat_if_not_set();
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("PB") || batter_event.starts_with("WP") {
                    // Passed ball or wild pitch
                    runner_dests.set_batter_still_at_bat_if_not_set();
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
                            if get_verbosity().is_at_least(Verbosity::Normal) {
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
                    runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::SecondBase).unwrap();
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("C/") || batter_event == "C" {
                    // catcher's interference
                    // this destination may get overridden
                    runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase).unwrap();
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("E") {
                    // error letting the runner reach base
                    // this destination may get overridden
                    runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase).unwrap();
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("FC") {
                    // fielder's choice
                    // this destination may get overridden
                    runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase).unwrap();
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("FLE") {
                    // error on fly foul ball. Nothing happens.
                    runner_dests.set_batter_still_at_bat_if_not_set();
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("SHE") {
                    // Error on sac hit (bunt).  Advances given explicitly
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.contains("DP") || batter_event.contains("TP") {
                    // Double or triple play
                    lazy_static! {
                        static ref DOUBLE_PLAY_RE : Regex = build_regex(r"^\d+\((\d|B)\)(?:\d*\((\d|B)\))?(?:\d*\((\d|B)\))?");
                    }
                    let double_play_captures = DOUBLE_PLAY_RE.captures(batter_event);
                    if let Some(double_play_captures) = double_play_captures {
                        if get_verbosity().is_at_least(Verbosity::Verbose) {
                            println!("double/triple play");
                        }
                        // The batter is out if the last character is a number, not ')'
                        // (unless there's a "(B)" in the string
                        let double_play_string = batter_event.split('/').next().unwrap();
                        if double_play_string.chars().last().unwrap() != ')' {
                            runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::Out).unwrap();
                        } else {
                            runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase).unwrap();
                        }
                        runner_dests.set(double_play_captures.get(1).unwrap().as_str().chars().next().unwrap().try_into()?, RunnerFinalPosition::Out).unwrap();
                        if let Some(second_group) = double_play_captures.get(2) {
                            runner_dests.set(second_group.as_str().chars().next().unwrap().try_into()?, RunnerFinalPosition::Out).unwrap();
                        }
                        if let Some(third_group) = double_play_captures.get(3) {
                            runner_dests.set(third_group.as_str().chars().next().unwrap().try_into()?, RunnerFinalPosition::Out).unwrap();
                        }
                        // Unfortunately, since it could be a caught fly ball and throw out,
                        // we have to assume runners can't go anywhere.
                        runners_default_stay_still = true;
                        done_parsing_event = true;
                    }
                }
            }
            if !done_parsing_event {
                lazy_static! {
                    static ref WEIRD_DOUBLE_PLAY_RE : Regex = build_regex(r"^\d+(/.*?)*/.?[DT]P");
                }
                if WEIRD_DOUBLE_PLAY_RE.is_match(batter_event) {
                    // This is a double play. The specifics of who's out will
                    // come later.
                    if get_verbosity().is_at_least(Verbosity::Verbose) {
                        println!("weird double/triple play");
                    }
                    runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::Out).unwrap();
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                lazy_static! {
                    static ref SIMPLE_OUT_RE : Regex = build_regex(r"^\d\D");
                }
                let very_simple_out = 
                    if batter_event.len() == 1 {
                        let batter_char = batter_event.chars().next().unwrap();
                        batter_char >= '1' && batter_char <= '9'
                    } else {
                        false
                    };
                if (SIMPLE_OUT_RE.is_match(batter_event) && !batter_event.contains("/FO")) || very_simple_out {
                    if get_verbosity().is_at_least(Verbosity::Verbose) {
                        println!("simple out");
                    }
                    lazy_static! {
                        static ref SIMPLE_OUT_ERROR_RE : Regex = build_regex(r"^\dE");
                    }
                    let is_error =  SIMPLE_OUT_ERROR_RE.is_match(batter_event);
                    runner_dests.set(RunnerInitialPosition::Batter, if is_error { RunnerFinalPosition::FirstBase } else { RunnerFinalPosition::Out }).unwrap();
                    // runners don't move unless explicit
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                lazy_static! {
                    static ref PUT_OUT_RE : Regex = build_regex(r"^\d*(\d).*?(?:\((.)\))?");
                }
                if let Some(put_out_captures) = PUT_OUT_RE.captures(batter_event) {
                    if get_verbosity().is_at_least(Verbosity::Verbose) {
                        println!("Got a putout");
                    }
                    lazy_static! {
                        static ref PUT_OUT_ERROR_RE : Regex = build_regex(r"\d?E\d");
                    }
                    if PUT_OUT_ERROR_RE.is_match(batter_event) {
                        // Error on the play - batter goes to first unless explicit
                        runner_dests.set(RunnerInitialPosition::Batter, RunnerFinalPosition::FirstBase).unwrap();
                    }
                    else {
                        default_batter_base = Some(RunnerFinalPosition::FirstBase);
                        if batter_event.contains("/FO") {
                            // Force out - this means the thing in parentheses
                            // is the runner who is out.
                            if get_verbosity().is_at_least(Verbosity::Verbose) {
                                println!("force out")
                            }
                            let out_from_base = put_out_captures.get(2).ok_or(anyhow!("force out didn't have which runner was out {}", batter_event))?.as_str();
                            let out_from_base: RunnerInitialPosition = out_from_base.chars().next().unwrap().try_into()?;
                            runner_dests.set(out_from_base, RunnerFinalPosition::Out)?;
                        }
                        else {
                            // Determine from put_out_captures.get(1) (who made out) and
                            // put_out_captures.get(2) (where out is) which base the out was at.
                            if let Some(runner_base) = put_out_captures.get(2) {
                                let runner: RunnerInitialPosition = runner_base.as_str().chars().next().unwrap().try_into()?;
                                runner_dests.set(runner, RunnerFinalPosition::Out)?;
                            }
                            else {
                                let out_at_base = put_out_captures.get(1).unwrap().as_str().parse::<u8>().map_err(|_| anyhow!("Base not an integer in batter_event {}", batter_event))?;
                                let out_at_base = RunnerFinalPosition::from_position(out_at_base);
                                if let Some(out_at_base_position) = out_at_base {
                                    out_at_bases.push(out_at_base_position);
                                }
                                else {
                                    // If we don't know what base it was, assume first base
                                    out_at_bases.push(RunnerFinalPosition::FirstBase);
                                }
                            }
                        }
                    }
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("BK") {
                    // Balk
                    runner_dests.set_batter_still_at_bat_if_not_set();
                    // Advance runners
                    // actually, this should be explicit, game NYA196209092
                    // has a balk where the runner doesn't advance from
                    // second??
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("CS") {
                    // Caught stealing
                    GameSituation::handle_cs_or_pocs_event(batter_event, &mut runner_dests)?;
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("SB") {
                    // stolen base (could be multiple)
                    GameSituation::handle_sb_event(batter_event, &mut runner_dests)?;
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("DI") {
                    // defensive indifference, runners resolved later
                    runner_dests.set_batter_still_at_bat_if_not_set();
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("OA") {
                    // runner advances somehow (resolved later)
                    runner_dests.set_batter_still_at_bat_if_not_set();
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                if batter_event.starts_with("POCS") {
                    // Pick-off (and caught stealing)
                    GameSituation::handle_cs_or_pocs_event(batter_event, &mut runner_dests)?;
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }
            if !done_parsing_event {
                // note that we already handled POCS
                if batter_event.starts_with("PO") {
                    // Pick-off
                    GameSituation::handle_po_event(batter_event, &mut runner_dests)?;
                    runners_default_stay_still = true;
                    done_parsing_event = true;
                }
            }

            if !done_parsing_event {
                return Err(anyhow!("ERROR - unrecognized event {} (line is {})", batter_event, line));
            }
        }

        // Now parse runner stuff
        if play_array.len() > 1 {
            let runner_array = play_array[1].split(';').into_iter().map(|x| x.trim());
            for runner_item in runner_array {
                let runner_chars = runner_item.chars().collect::<SmallVec<[char;10]>>();
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
                        if initial_runner.base_number() > final_runner.base_number()? {
                            return Err(anyhow!(format!("Runner went backwards from {:?} to {:?} for play {}", initial_runner, final_runner, play_string)));
                        }
                        runner_dests.set(initial_runner, final_runner)?;
                    },
                    'X' => {
                        lazy_static! {
                            static ref RUNNER_OUT_ERROR_RE : Regex = build_regex(r"^...(?:\([^)]*?\))*\(\d*E.*\)");
                        }
                        if RUNNER_OUT_ERROR_RE.is_match(runner_item) {
                            // So this is probably an error.  See if the intervening
                            // parentheses indicate an out
                            lazy_static! {
                                static ref RUNNER_OUT_ERROR_ACTUAL_OUT_1_RE : Regex = build_regex(r"^....*?\(\d*(/TH)?\).*?\(\d*E.*\)");
                                static ref RUNNER_OUT_ERROR_ACTUAL_OUT_2_RE : Regex = build_regex(r"^....*?\(\d*E.*\)\(\d*\)");
                            }
                            if RUNNER_OUT_ERROR_ACTUAL_OUT_1_RE.is_match(runner_item) || RUNNER_OUT_ERROR_ACTUAL_OUT_2_RE.is_match(runner_item) {
                                // Yup, this is really an out.
                                runner_dests.set(initial_runner, RunnerFinalPosition::Out)?;
                            }
                            else {
                                // Nope, so runner is safe
                                if initial_runner.base_number() > final_runner.base_number()? {
                                    return Err(anyhow!(format!("Runner went backwards from {:?} to {:?} for play {}", initial_runner, final_runner, play_string)));
                                }
                                runner_dests.set(initial_runner, final_runner)?;
                            }
                        }
                        else {
                            runner_dests.set(initial_runner, RunnerFinalPosition::Out)?;
                        }
                    },
                    _ => return Err(anyhow!(format!("Invalid character {} in runner specification for play {}", runner_chars[1], play_string)))
                };
            }
        }

        Self::process_out_at_base(&out_at_bases, &mut runner_dests)?;

        // Deal with runner_dests
        return self.resolve_runners_and_outs(
            &mut runner_dests,
            &default_batter_base,
            runners_default_stay_still,
            &game_rule_options);
    }

    fn process_out_at_base(out_at_bases: &[RunnerFinalPosition], runner_dests: &mut RunnerDests) -> Result<()> {
        for out_at_base in out_at_bases {
            // Find the closest unresolved runner behind that base
            let possible_runners =
                runner_dests.keys()
                    .filter(|s| runner_dests.get(*s).unwrap() == RunnerFinalPosition::Undetermined)
                    .filter(|s| s.base_number() < out_at_base.base_number().unwrap())
                    .max_by(|x, y| x.base_number().cmp(&y.base_number()));
            let closest_runner = possible_runners.ok_or(anyhow!("Couldn't find closest runner to base {:?}", out_at_base))?;
            if get_verbosity().is_at_least(Verbosity::Verbose) {
                println!("Picked runner {:?} for out_at_base {:?}", closest_runner, out_at_base);
            }
            runner_dests.set(closest_runner, RunnerFinalPosition::Out).unwrap();
        }
        Ok(())
    }

    fn resolve_runners_and_outs(self: &Self,
        runner_dests: &mut RunnerDests,
        default_batter_base: &Option<RunnerFinalPosition>,
        runners_default_stay_still: bool,
        game_rule_options: &GameRuleOptions) -> Result<GameSituation> {
        if let Some(default_batter_base) = default_batter_base {
            if runner_dests.get(RunnerInitialPosition::Batter).unwrap() == RunnerFinalPosition::Undetermined {
                runner_dests.set(RunnerInitialPosition::Batter, *default_batter_base).unwrap();
            }
        }
        let mut new_situation = self.clone();
        new_situation.runners = [false, false, false];
        let mut undetermined_runner = None;
        let mut duplicate_runner = None;
        for key in runner_dests.keys() {
            let dest = runner_dests.get(key).unwrap();
            match dest {
                RunnerFinalPosition::Out => {
                    new_situation.outs += 1;
                },
                RunnerFinalPosition::HomePlate => {
                    new_situation.cur_score_diff += 1;
                },
                RunnerFinalPosition::Undetermined => {
                    // if key is Batter, we're in trouble below regardless
                    // (unless we have 3 outs, but we can't check that yet)
                    if runners_default_stay_still && key != RunnerInitialPosition::Batter {
                        if *new_situation.runners.get(key.runner_index()?).unwrap() {
                            duplicate_runner = Some(key.runner_index()?);
                        }
                        *(new_situation.runners.get_mut(key.runner_index()?).unwrap()) = true;
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
                    if *new_situation.runners.get(dest.runner_index()?).unwrap() {
                        duplicate_runner = Some(dest.runner_index()?);
                    }
                    *(new_situation.runners.get_mut(dest.runner_index()?).unwrap()) = true;
                }
            }
        }
        if new_situation.outs < 3 {
            if undetermined_runner.is_some() {
                return Err(anyhow!("Got undetermined runner {:?} with less than three outs!", undetermined_runner.unwrap()))
            }
            if duplicate_runner.is_some() {
                /*if get_verbosity().is_at_least(Verbosity::Normal) {
                    println!("ERROR - already a runner at base {}!", duplicate_runner.unwrap());
                }*/
                return Err(anyhow!("ERROR - duplicate runner at base {}", duplicate_runner.unwrap()));
            }
        }
        new_situation.next_inning_if_three_outs(game_rule_options.runner_starts_on_second_in_extra_innings, game_rule_options.innings);
        Ok(new_situation)
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
            let start: RunnerInitialPosition = (dest.base_number()? - 1).to_string().chars().next().unwrap().try_into()?;
            runner_dests.set(start, dest)?;
            runner_dests.set_batter_still_at_bat_if_not_set();
        }
        Ok(())
    }

    fn handle_cs_or_pocs_event(cs_event: &str, runner_dests: &mut RunnerDests) -> Result<()> {
        assert!(cs_event.starts_with("CS") || cs_event.starts_with("POCS"));
        lazy_static! {
            static ref CS_ERROR_RE : Regex = build_regex(r"^(?:PO)?CS.\([^)]*?E.*?\)");
        }
        let dest_position = if cs_event.starts_with("CS") { 2 } else { 4 };
        let dest: RunnerFinalPosition = cs_event.chars().nth(dest_position)
            .ok_or(anyhow!("CS line too short {}", cs_event))?.try_into()?;
        if dest == RunnerFinalPosition::FirstBase {
            return Err(anyhow!("CS to first base?: {}", cs_event));
        }
        let start: RunnerInitialPosition = (dest.base_number()? - 1).to_string().chars().next().unwrap().try_into()?;

        if CS_ERROR_RE.is_match(cs_event) {
            // Error, so no out.
            runner_dests.set(start, dest)?;
        }
        else {
            runner_dests.set(start, RunnerFinalPosition::Out)?;
        }
        runner_dests.set_batter_still_at_bat_if_not_set();
        Ok(())
    }

    fn handle_po_event(po_event: &str, runner_dests: &mut RunnerDests) -> Result<()> {
        assert!(po_event.starts_with("PO"));
        lazy_static! {
            static ref PO_ERROR_RE : Regex = build_regex(r"^PO.\([^)]*?E.*?\)");
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
            runner_dests.set(start, RunnerFinalPosition::Out)?;
        }
        runner_dests.set_batter_still_at_bat_if_not_set();
        Ok(())
    }
}
#[derive(Clone, Debug, PartialEq, Eq)]
struct PlayLineInfo<'a> {
    inning: Inning,
    player_id: &'a str,
    count_when_play_happened: &'a str,
    pitches_str: &'a str,
    play_str: SmolStr
}

impl<'a> From<&'a str> for PlayLineInfo<'a> {
    fn from(line: &'a str) -> Self {
        lazy_static! {
            static ref PLAY_RE : Regex = build_regex(r"^play,\s?(\d+),\s?([01]),(.*?),(.*?),(.*?),(.*)$");
        }
        let play_match = PLAY_RE.captures(line).unwrap();
        // remove characters we don't care about
        let play_str: SmolStr = play_match.get(6).unwrap().as_str().chars()
            .filter(|&x| x != '!' && x != '#' && x != '?').collect();
        Self {
            inning: Inning { number: play_match.get(1).unwrap().as_str().parse::<u8>().unwrap(),
                is_home: play_match.get(2).unwrap().as_str() == "1"},
            player_id: play_match.get(3).unwrap().as_str(),
            count_when_play_happened: play_match.get(4).unwrap().as_str(),
            pitches_str: play_match.get(5).unwrap().as_str(),
            play_str: play_str
        }
    }
}

fn parse_file<P>(filename: P, reports: &mut Vec<Box<dyn Report>>) -> Result<u32>
where P: Debug + AsRef<Path> {
    let mut cur_game_situation = GameSituation::new();
    let mut all_game_situations : Vec<GameSituation> = Vec::new();
    let mut play_lines : Vec<String> = Vec::new();
    let mut in_game = false;
    let mut num_games = 0;
    let mut cur_id = "".to_owned();
    if get_verbosity().is_at_least(Verbosity::Normal) {
        println!("{:?}", filename);
    }
    let filename_extension = filename.as_ref().extension().unwrap().to_str().unwrap();
    let is_playoffs = filename_extension.to_uppercase() == "EVE";
    fn start_new_game_from_line(line: &str, cur_id: &mut String, cur_game_situation: &mut GameSituation,
        all_game_situations: &mut Vec<GameSituation>, play_lines: &mut Vec<String>,
        game_rule_options: &mut GameRuleOptions, is_playoffs: bool) {
        *cur_id = line[3..].to_owned();
        *cur_game_situation = GameSituation::new();
        all_game_situations.clear();
        all_game_situations.push(*cur_game_situation);
        play_lines.clear();
        let year = year_from_game_id(cur_id);
        // In 2020 a runner started on second base in extra innings, but not in playoff games.
        game_rule_options.runner_starts_on_second_in_extra_innings = year == 2020 && !is_playoffs;
        game_rule_options.innings = 9;
    }
    fn finish_game(cur_id: &mut String, cur_game_situation: &GameSituation, all_game_situations: &mut Vec<GameSituation>,
        play_lines: &mut Vec<String>, reports: &mut Vec<Box<dyn Report>>, num_games: &mut u32,
        game_rule_options: &GameRuleOptions) {
        // Don't include the last situation in the list of keys, because it's one after the last inning probably
        if Some(cur_game_situation) == all_game_situations.last() {
            all_game_situations.remove(all_game_situations.len() - 1);
        }
        for report in &mut *reports {
            report.processed_game(&cur_id,
                    &cur_game_situation,
                    &all_game_situations,
                    &play_lines,
                    game_rule_options);
        }
        *num_games = *num_games + 1;
    }

    // files use ISO-8859-1 encoding (i.e. "latin1"), not utf-8
    // https://stackoverflow.com/questions/45788866/how-to-read-a-gbk-encoded-file-into-a-string
    let file = File::open(filename)?;
    let reader = io::BufReader::new(file);
    let lines = reader.split(b'\n').map(|l| l.unwrap());
    let mut game_rule_options = GameRuleOptions { runner_starts_on_second_in_extra_innings: false, innings: 9 };
    for line in lines {
        let line = ISO_8859_1.decode(&line, DecoderTrap::Strict).unwrap();
        let line = line.trim();
        if !in_game {
            if line.starts_with("id,") {
                in_game = true;
                start_new_game_from_line(&line, &mut cur_id, &mut cur_game_situation,
                    &mut all_game_situations, &mut play_lines, &mut game_rule_options, is_playoffs);
            }
        }
        else {
            if line.starts_with("play,") {
                let new_situation = cur_game_situation.parse_play(&line, &game_rule_options);
                match new_situation {
                    Err(error) => {
                        if !is_known_bad_game(&cur_id) {
                            panic!("Error in game {} at line \"{}\"  error is {}  initial situation {:?}", cur_id, line, error, cur_game_situation);
                        }
                        in_game = false;
                    }
                    Ok(new_situation) => {
                        //if cur_id == "BAL195704270" {
                        //    println!("After line {}, situation is {:?}", line, new_situation);
                        //}
                        if all_game_situations.last() != Some(&new_situation) {
                            all_game_situations.push(new_situation);
                            play_lines.push(line.to_owned());
                        }
                        cur_game_situation = new_situation;
                    }
                }
            }
            else if line.starts_with("id,") {
                finish_game(&mut cur_id, &cur_game_situation, &mut all_game_situations,
                    &mut play_lines, reports, &mut num_games, &game_rule_options);

                start_new_game_from_line(&line, &mut cur_id, &mut cur_game_situation,
                    &mut all_game_situations, &mut play_lines, &mut game_rule_options, is_playoffs);
            }
            else if line.starts_with("info,innings,") {
                game_rule_options.innings = line["info,innings,".len()..].parse::<u8>().unwrap();
            }
        }
    }
    if all_game_situations.len() > 0 {
        finish_game(&mut cur_id, &cur_game_situation, &mut all_game_situations,
            &mut play_lines, reports, &mut num_games, &game_rule_options);
    }

    Ok(num_games)
}

fn get_ball_strike_counts_from_pitches(pitches: &str) -> SmallVec<[BallsStrikes;8]> {
    lazy_static! {
        // This is surprisingly complicated because there's a lot of extraneous stuff in here.
        // Ignore irrelevant stuff as well as the final result of a pitch (if it goes in play)
        static ref IGNORE_CHARS: HashSet<char> = "!#?+*.123>HNXY "
            .chars().collect();
        static ref BALL_CHARS: HashSet<char> = "BIPV"
            .chars().collect();
        static ref STRIKE_CHARS: HashSet<char> = "CKLMOQST"
            .chars().collect();
        static ref FOUL_BALL_CHARS: HashSet<char> = "FR"
            .chars().collect();
    }
    let mut counts: SmallVec<[BallsStrikes;8]> = smallvec![BallsStrikes::new()];
    for pitch in pitches.chars() {
        let pitch = pitch.to_ascii_uppercase();
        // For performance, check in rough order of frequency
        if STRIKE_CHARS.contains(&pitch) {
            counts.push(counts.last().unwrap().add_strike());
        }
        else if BALL_CHARS.contains(&pitch) {
            counts.push(counts.last().unwrap().add_ball());
        }
        else if FOUL_BALL_CHARS.contains(&pitch) {
            if counts.last().unwrap().strikes != 2 {
                counts.push(counts.last().unwrap().add_strike());
            }
        }
        else if !IGNORE_CHARS.contains(&pitch) {
            // This is some character we don't recognize
            if pitch != 'U' {
                if get_verbosity().is_at_least(Verbosity::Normal) {
                    println!("Unknown pitch {} in {}, skipping", pitch, pitches);
                }
            }
            return smallvec![BallsStrikes::new()];
        }
    }
    counts
}

trait Report : Any + Send + Sync {
    fn processed_game(self: &mut Self, game_id: &str, final_game_situation: &GameSituation,
        situations: &[GameSituation], play_lines: &[String], game_rule_options: &GameRuleOptions);
    fn clear_stats(self: &mut Self);
    /// "other" parameter must be of the same type
    fn merge_into(self: &Self, other: &mut dyn Any);
    fn supports_parallel_processing(self: &Self) -> bool { true }
    fn done_with_year<'a>(self: &'a mut Self, year: usize);
    fn done_with_all<'a>(self: &'a mut Self);
    fn make_new(&self) -> Box<dyn Report>;
    fn name(&self) -> &'static str;
    // https://stackoverflow.com/questions/33687447/how-to-get-a-reference-to-a-concrete-type-from-a-trait-object
    fn as_any_mut(&mut self) -> &mut dyn Any;
}

trait StatsReport : Any + Send + Sync {
    type Key : PartialOrd;
    type Value;
    fn get_stats<'a>(&'a self) -> &'a HashMap<Self::Key, Self::Value>;
    fn write_key<T:Write>(&self, file: &mut T, key: &Self::Key);
    fn write_value<T:Write>(&self, file: &mut T, value: &Self::Value);
    fn write_extra<T:Write>(&self, _file: &mut T, _key: &Self::Key, _value: &Self::Value) {}
    fn report_file_name() -> &'static str;
    fn make_new_impl(&self) -> Box<dyn Report>;
    fn name_impl(&self) -> &'static str;
    fn processed_game_impl(self: &mut Self, game_id: &str, final_game_situation: &GameSituation,
        situations: &[GameSituation], play_lines: &[String], game_rule_options: &GameRuleOptions);
    fn clear_stats_impl(self: &mut Self);
    /// "other" parameter must be of the same type
    fn merge_into_impl(self: &Self, other: &mut dyn Any);

    fn done_with_all_impl(self: &mut Self) {
        let mut contents: Vec<_> = self.get_stats().iter().collect();
        contents.sort_by(|a, b| a.0.partial_cmp(b.0).unwrap());
        let mut path_parts = vec![".."];
        path_parts.extend(Self::report_file_name().split("/").into_iter());
        let mut output = File::create(path_parts.iter().collect::<PathBuf>()).unwrap();
        for entry in contents {
            self.write_key(&mut output, entry.0);
            write!(output, ": ").unwrap();
            self.write_value(&mut output, entry.1);
            writeln!(output, "").unwrap();
            self.write_extra(&mut output, entry.0, entry.1);
        }
    }

    fn done_with_year_impl(self: &mut Self, year: usize) {
        let path: PathBuf = ["..", "statsyears", &format!("{}.{}", Self::report_file_name(), year.to_string())].iter().collect();
        let mut contents: Vec<_> = self.get_stats().iter().collect();
        contents.sort_by(|a, b| a.0.partial_cmp(b.0).unwrap());
        let mut output = BufWriter::new(File::create(path).unwrap());
        for entry in contents {
            self.write_key(&mut output, entry.0);
            write!(output, ": ").unwrap();
            self.write_value(&mut output, entry.1);
            writeln!(output, "").unwrap();
        }
        output.flush().unwrap();
    }
}

impl<T> Report for T
    where T: StatsReport {
    fn processed_game(self: &mut Self, game_id: &str, final_game_situation: &GameSituation,
        situations: &[GameSituation], play_lines: &[String], game_rule_options: &GameRuleOptions) {
        
        // TODO - allow opting out of these?
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

        self.processed_game_impl(game_id, final_game_situation, situations, play_lines, game_rule_options);
    }

    fn clear_stats(self: &mut Self) {
        self.clear_stats_impl()
    }

    fn merge_into(self: &Self, other: &mut dyn Any) {
        self.merge_into_impl(other)
    }

    fn done_with_year(self: &mut Self, year: usize) {
        self.done_with_year_impl(year);
    }

    fn done_with_all(self: &mut Self) {
        self.done_with_all_impl();
    }

    fn make_new(&self) -> Box<dyn Report> {
        self.make_new_impl()
    }

    fn name(&self) -> &'static str {
        self.name_impl()
    }

    fn as_any_mut(&mut self) -> &mut dyn Any { self }
}

#[derive(FromArgs)]
/// Options
struct Options {
    /// quiet output
    #[argh(switch, short='q')]
    quiet: bool,
    /// verbose output
    #[argh(switch, short='v')]
    verbose: bool,
    /// generate data on a per-year basis
    #[argh(switch, short='y')]
    by_year: bool,
    /// which reports to run.  Defaults to Stats.
    /// Run with an invalid report (like "abc") to see the
    /// valid options.
    #[argh(option, short='r')]
    reports: Option<String>,
    #[argh(positional)]
    file_patterns: Vec<String>
}

impl Options {
    pub fn get_verbosity(&self) -> Result<Verbosity> {
        if self.quiet && self.verbose {
            return Err(anyhow!("can't specify quiet and verbose!"));
        }
        if self.verbose {
            Ok(Verbosity::Verbose)
        }
        else if self.quiet {
            Ok(Verbosity::Quiet)
        }
        else {
            Ok(Verbosity::Normal)
        }
    }
}

fn is_known_bad_game(game_id: &str) -> bool {
    lazy_static! {
        static ref KNOWN_BAD_GAMES: HashSet<&'static str> =
            ["WS2196605270", "MIL197107272", "MON197108040", "NYN198105090", "SEA200709261", "MIL201304190", "BAL201906250"]
            .iter().cloned().collect();
    }
    return KNOWN_BAD_GAMES.contains(game_id);
}

fn get_reports(report_id: &Option<String>) -> Result<Vec<Box<dyn Report>>> {
    lazy_static! {
        // First one in the list is also the default
        static ref REPORTS : &'static [(&'static str, fn() -> Vec<Box<dyn Report>>)] = &[
            ("Stats", (|| vec![
                Box::new(reports::StatsWinExpectancyReport::new()),
                Box::new(reports::StatsRunExpectancyPerInningReport::new())])
            ),
            ("StatsWithBallsStrikes", (|| vec![
                Box::new(reports::StatsWinExpectancyWithBallsStrikesReport::new()),
                Box::new(reports::StatsRunExpectancyPerInningWithBallsStrikesReport::new())])
            ),
            ("HomeTeamDownSixWithTwoOutsInNinth", (|| vec![
                Box::new(reports::HomeTeamDownSixWithTwoOutsInNinthReport::new())])
            ),
            ("SpecificSituationKeys", (|| vec![
                Box::new(reports::SpecificSituationKeysReport::new())])
            ),
            ("WalkOffWalk", (|| vec![
                Box::new(reports::WalkOffWalkReport::new())])
            ),
            ("CountsToWalksAndStrikeouts", (|| vec![
                Box::new(reports::CountsToWalksAndStrikeoutsReport::new())])
            ),
            ("BasesLoadedNoOutsNoRuns", (|| vec![
                Box::new(reports::BasesLoadedNoOutsNoRunsReport::new())])
            ),
            ("RunExpectancyPerInning", (|| vec![
                Box::new(reports::StatsRunExpectancyPerInningByInningReport::new())])
            ),
        ];
    }
    match report_id {
        None => Ok(REPORTS[0].1()),
        Some(report_key) => {
            for (key, function) in REPORTS.iter() {
                if key == report_key {
                    return Ok(function());
                }
            }
            let mut error = format!("Invalid report \"{}\" - valid reports are:\n", report_key);
            for (key, _) in REPORTS.iter() {
                error.push_str(&format!("    {}\n", key));
            }
            Err(anyhow!(error))
        }
    }
}

static mut VERBOSITY: Verbosity = Verbosity::Normal;
fn get_verbosity() -> Verbosity {
    // This is safe; we only set it before calling stuff
    unsafe {
        return VERBOSITY;
    }
}

fn year_from_game_id(game_id: &str) -> u32 {
    game_id[3..7].parse().unwrap()
}

fn main() -> Result<()> {
    let mut options : Options = argh::from_env();
    let mut reports: Vec<Box<dyn Report>> = get_reports(&options.reports)?;
    let mut num_games = 0;
    unsafe {
        VERBOSITY = options.get_verbosity()?;
    }
    let do_parallel = true;
    if do_parallel && reports.iter().any(|x| !x.supports_parallel_processing())
        && get_verbosity().is_at_least(Verbosity::Normal) {
        println!("Not running in parallel because the following reports don't support it: {}",
            reports.iter()
                .filter(|x| !x.supports_parallel_processing())
                .map(|x| x.name())
                .fold(String::new(), |s, arg| s + &arg + ", "));
    }
    if options.file_patterns.is_empty() {
        options.file_patterns.push(["..", "data", "*"].iter().collect::<PathBuf>().to_str().unwrap().to_string());
    }
    if options.by_year {
        let mut years_to_files: HashMap<usize, Vec<PathBuf>> = HashMap::new();
        for pattern in options.file_patterns {
            for path in glob(&pattern).expect("Failed to read glob pattern") {
                let path = path?;
                let year: usize = path.file_name().unwrap().to_str().unwrap()[0..4].parse().unwrap();
                let year_list = years_to_files.entry(year).or_default();
                year_list.push(path);
            }
        }
        let mut years: Vec<_> = years_to_files.keys().collect();
        years.sort();
        if do_parallel {
            // Just do one thread per year here, close enough to optimal
            num_games = years
                .par_iter()
                .map(|&year| {
                    let mut local_num_games = 0;
                    {
                        let mut local_reports: Vec<Box<dyn Report>> = reports.iter().map(|report| report.make_new()).collect();
                        for path in years_to_files.get(year).unwrap() {
                            local_num_games += parse_file(path, &mut local_reports).unwrap();
                        }
                        for mut report in local_reports.drain(..) {
                            report.done_with_year(*year);
                        }
                    }
                    local_num_games
                })
                .sum();
            println!("Parsed {} games", num_games);
        }
        else {
            for year in years {
                for report in reports.iter_mut() {
                    report.clear_stats();
                }
                for path in years_to_files.get(year).unwrap() {
                    num_games += parse_file(path, &mut reports)?;
                }
                for report in &mut reports {
                    report.done_with_year(*year);
                }
            }
        }
    }
    else {
        if do_parallel {
            let paths: Vec<_> = options.file_patterns.iter()
                .map(|pattern| glob(&pattern).expect("Failed to read glob pattern").map(|x| x.unwrap()))
                .flatten().into_iter().collect();
            let final_reports = paths
                .par_iter()
                .map(|path| {
                    // PERF - would be nice to only create one report per thread and re-use it,
                    // but I can't find a way in rayon to do that.
                    let mut local_reports: Vec<Box<dyn Report>> = reports.iter().map(|report| report.make_new()).collect();
                    let local_num_games = parse_file(path, &mut local_reports).unwrap();
                    (local_reports, local_num_games)
                })
                .fold(|| {
                    let new_reports: Vec<Box<dyn Report>> = reports.iter().map(|report| report.make_new()).collect();
                    (new_reports, 0)
                }, |mut start, new| {
                    for i in 0..start.0.len() {
                        new.0[i].merge_into(start.0[i].as_any_mut());
                    }
                    (start.0, start.1 + new.1)
                })
                .reduce(|| {
                    let new_reports: Vec<Box<dyn Report>> = reports.iter().map(|report| report.make_new()).collect();
                    (new_reports, 0)
                }, |mut start, new| {
                    for i in 0..start.0.len() {
                        new.0[i].merge_into(start.0[i].as_any_mut());
                    }
                    (start.0, start.1 + new.1)
                });
            let num_games = final_reports.1;
            let final_reports = final_reports.0;
            println!("Parsed {} games", num_games);
            for mut report in final_reports {
                report.done_with_all();
            }
        }
        else {
            for pattern in options.file_patterns {
                for path in glob(&pattern).expect("Failed to read glob pattern") {
                    num_games += parse_file(path?, &mut reports)?;
                }
            }
            println!("Parsed {} games", num_games);
            for mut report in reports {
                report.done_with_all();
            }
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    #![allow(non_snake_case)]
    use std::collections::HashMap;
    use data::*;
    use super::*;

    #[test]
    fn test_next_inning_if_three_outs__zero_outs() {
        for runner_starts_on_second_in_extra_innings in [false, true].iter() {
            let orig_inning = GameSituation {
                cur_score_diff: 2,
                inning: Inning::new(),
                outs: 0,
                runners: [false, true, false]
            };
            let mut new_inning = orig_inning.clone();
            new_inning.next_inning_if_three_outs(*runner_starts_on_second_in_extra_innings, 9);
            assert_eq!(orig_inning, new_inning);
        }
    }

    #[test]
    fn test_next_inning_if_three_outs__one_out() {
        for runner_starts_on_second_in_extra_innings in [false, true].iter() {
            let orig_inning = GameSituation {
                cur_score_diff: 2,
                inning: Inning::new(),
                outs: 1,
                runners: [false, true, false]
            };
            let mut new_inning = orig_inning.clone();
            new_inning.next_inning_if_three_outs(*runner_starts_on_second_in_extra_innings, 9);
            assert_eq!(orig_inning, new_inning);
        }
    }

    #[test]
    fn test_next_inning_if_three_outs__two_outs() {
        for runner_starts_on_second_in_extra_innings in [false, true].iter() {
            let orig_inning = GameSituation {
                cur_score_diff: 2,
                inning: Inning::new(),
                outs: 2,
                runners: [false, true, false]
            };
            let mut new_inning = orig_inning.clone();
            new_inning.next_inning_if_three_outs(*runner_starts_on_second_in_extra_innings, 9);
            assert_eq!(orig_inning, new_inning);
        }
    }

    #[test]
    fn test_next_inning_if_three_outs__three_outs_home() {
        for runner_starts_on_second_in_extra_innings in [false, true].iter() {
            let mut orig_inning = GameSituation {
                cur_score_diff: 2,
                inning: Inning { number: 1, is_home: true},
                outs: 3,
                runners: [false, true, false]
            };
            orig_inning.next_inning_if_three_outs(*runner_starts_on_second_in_extra_innings, 9);
            assert_eq!(GameSituation {
                cur_score_diff: -2,
                inning: Inning { number: 2, is_home: false},
                outs: 0,
                runners: [false, false, false]
            }, orig_inning);
        }
    }

    #[test]
    fn test_next_inning_if_three_outs__three_outs_visitor() {
        for runner_starts_on_second_in_extra_innings in [false, true].iter() {
            let mut orig_inning = GameSituation {
                cur_score_diff: 2,
                inning: Inning::new(),
                outs: 3,
                runners: [false, true, false]
            };
            orig_inning.next_inning_if_three_outs(*runner_starts_on_second_in_extra_innings, 9);
            assert_eq!(GameSituation {
                cur_score_diff: -2,
                inning: Inning { number: 1, is_home: true},
                outs: 0,
                runners: [false, false, false]
            }, orig_inning);
        }
    }

    fn make_extra_inning_game_situation(inning: Inning) -> GameSituation {
        GameSituation {
            cur_score_diff: 2,
            inning,
            outs: 3,
            runners: [false, true, false]
        }
    }

    #[test]
    fn test_next_inning_if_three_outs_ninth_inning__no_extra_runner() {
        for runner_starts_on_second_in_extra_innings in [false, true].iter() {
            for last_inning in [7, 8, 9, 10].iter() {
                let mut orig_inning = make_extra_inning_game_situation(Inning { number: *last_inning, is_home: false});
                orig_inning.next_inning_if_three_outs(*runner_starts_on_second_in_extra_innings, *last_inning);
                assert_eq!(false, orig_inning.runners[1]);
            }
        }
    }

    #[test]
    fn test_next_inning_if_three_outs_extra_innings__three_outs_visitor() {
        for runner_starts_on_second_in_extra_innings in [false, true].iter() {
            for last_inning in [7, 8, 9, 10].iter() {
                let mut orig_inning = make_extra_inning_game_situation(Inning { number: *last_inning + 1, is_home: false});
                orig_inning.next_inning_if_three_outs(*runner_starts_on_second_in_extra_innings, *last_inning);
                assert_eq!(*runner_starts_on_second_in_extra_innings, orig_inning.runners[1]);
            }
        }
    }
    #[test]
    fn test_next_inning_if_three_outs_eighth_inning__three_outs_home() {
        for runner_starts_on_second_in_extra_innings in [false, true].iter() {
            for last_inning in [7, 8, 9, 10].iter() {
                let mut orig_inning = make_extra_inning_game_situation(Inning { number: *last_inning - 1, is_home: true});
                orig_inning.next_inning_if_three_outs(*runner_starts_on_second_in_extra_innings, *last_inning);
                assert_eq!(false, orig_inning.runners[1]);
            }
        }
    }

    #[test]
    fn test_next_inning_if_three_outs_ninth_inning__three_outs_home() {
        for runner_starts_on_second_in_extra_innings in [false, true].iter() {
            for last_inning in [7, 8, 9, 10].iter() {
                let mut orig_inning = make_extra_inning_game_situation(Inning { number: *last_inning, is_home: true});
                orig_inning.next_inning_if_three_outs(*runner_starts_on_second_in_extra_innings, *last_inning);
                assert_eq!(*runner_starts_on_second_in_extra_innings, orig_inning.runners[1]);
            }
        }
    }

    #[test]
    fn test_next_inning_if_three_outs_tenth_inning__three_outs_home() {
        for runner_starts_on_second_in_extra_innings in [false, true].iter() {
            for last_inning in [7, 8, 9, 10].iter() {
                let mut orig_inning = make_extra_inning_game_situation(Inning { number: *last_inning + 1, is_home: true});
                orig_inning.next_inning_if_three_outs(*runner_starts_on_second_in_extra_innings, *last_inning);
                assert_eq!(*runner_starts_on_second_in_extra_innings, orig_inning.runners[1]);
            }
        }
    }

    #[test]
    fn test_is_home_winning__home_inning_tied() {
        let mut game = GameSituation::new();
        game.inning.is_home = true;
        game.cur_score_diff = 0;
        assert_eq!(None, game.is_home_winning());
    }

    #[test]
    fn test_is_home_winning__visitor_inning_tied() {
        let mut game = GameSituation::new();
        game.inning.is_home = false;
        game.cur_score_diff = 0;
        assert_eq!(None, game.is_home_winning());
    }

    #[test]
    fn test_is_home_winning__home_inning_home_ahead() {
        let mut game = GameSituation::new();
        game.inning.is_home = true;
        game.cur_score_diff = 2;
        assert_eq!(Some(true), game.is_home_winning());
    }

    #[test]
    fn test_is_home_winning__home_inning_visitor_ahead() {
        let mut game = GameSituation::new();
        game.inning.is_home = true;
        game.cur_score_diff = -2;
        assert_eq!(Some(false), game.is_home_winning());
    }

    #[test]
    fn test_is_home_winning__visitor_inning_home_ahead() {
        let mut game = GameSituation::new();
        game.inning.is_home = false;
        game.cur_score_diff = -2;
        assert_eq!(Some(true), game.is_home_winning());
    }

    #[test]
    fn test_is_home_winning__visitor_inning_visitor_ahead() {
        let mut game = GameSituation::new();
        game.inning.is_home = false;
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
            assert_eq!(expected.len(), dests.keys().count(), "{:?}", runners);
            for (key, expectedValue) in expected {
                assert_eq!(Some(expectedValue), dests.get(key), "{:?} {:?}", runners, key);
            }
        }
    }

    #[test]
    fn test_parse_play_line_info() {
        let play_line_info_str = "play,4,1,corrc001,22,BSBFFX,HR/78/F";
        let play_line_info = PlayLineInfo::from(play_line_info_str);
        let expected = PlayLineInfo {
            inning: Inning { number: 4, is_home: true}, 
            player_id: "corrc001",
            count_when_play_happened: "22",
            pitches_str: "BSBFFX",
            play_str: SmolStr::new("HR/78/F")
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

    mod ball_strike_tests {
        use super::*;

        fn test_ball_strikes(pitches: &str, expected_ball_strikes: &[(u8, u8)]) {
            let expected_counts: SmallVec<[BallsStrikes;8]> =
                expected_ball_strikes.iter().map(|(b, s)| BallsStrikes { balls: *b, strikes: *s }).collect();
            assert_eq!(expected_counts, get_ball_strike_counts_from_pitches(pitches));
        }

        #[test]
        fn test_empty_string() {
            test_ball_strikes("", &[(0, 0)]);
        }

        #[test]
        fn test_all_balls() {
            test_ball_strikes("IPVB", &[(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)]);
        }

        #[test]
        fn test_all_strikes_with_ignore_chars() {
            test_ball_strikes("+*.123>CNS>.*2K", &[(0, 0), (0, 1), (0, 2), (0, 3)]);
        }

        #[test]
        fn test_balls_and_strikes() {
            test_ball_strikes("LBMBBO", &[(0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (3, 2), (3, 3)]);
        }

        #[test]
        fn test_hit_first_pitch() {
            test_ball_strikes("X", &[(0, 0)]);
        }

        #[test]
        fn test_hit_later_pitch() {
            test_ball_strikes("QTX", &[(0, 0), (0, 1), (0, 2)]);
        }

        #[test]
        fn test_unknown_pitch_return_nothing() {
            test_ball_strikes("SBSUBBB", &[(0, 0)]);
        }

        #[test]
        fn test_foul_zero_strikes() {
            test_ball_strikes("BFY", &[(0, 0), (1, 0), (1, 1)]);
        }

        #[test]
        fn test_foul_one_strike() {
            test_ball_strikes("BSFX", &[(0, 0), (1, 0), (1, 1), (1, 2)]);
        }

        #[test]
        fn test_multiple_fouls_two_strikes() {
            test_ball_strikes("SBSFBFFX", &[(0, 0), (0, 1), (1, 1), (1, 2), (2, 2)]);
        }

        #[test]
        fn test_lots_of_fouls() {
            test_ball_strikes("BFFBFFBX", &[(0, 0), (1, 0), (1, 1), (1, 2), (2, 2), (3, 2)]);
        }
    }

    mod parse_play_tests {
        #![allow(non_snake_case)]
        use super::*;

        fn setup_with_inning(outs: u8, is_home: bool, runners: [bool;3], play_string: &str) -> (GameSituation, String) {
            let situation = GameSituation {
                runners,
                inning: Inning { number: 1, is_home },
                cur_score_diff: 0,
                outs,
            };

            (situation, format!("play,1,{},,,,{}", if situation.inning.is_home { 1 } else { 0 }, play_string))
        }

        fn setup(runners: [bool;3], play_string: &str) -> (GameSituation, String) {
            let situation = GameSituation {
                runners,
                inning: Inning::new(),
                cur_score_diff: 0,
                outs: 0,
            };

            (situation, format!("play,1,{},,,,{}", if situation.inning.is_home { 1 } else { 0 }, play_string))
        }

        fn assert_result(expected_situation: &GameSituation, initial_situation: &GameSituation, play_line: &str) -> Result<()> {
            let game_rule_options = GameRuleOptions { runner_starts_on_second_in_extra_innings: false, innings: 9 };
            let new_situation = initial_situation.parse_play(&play_line, &game_rule_options)?;
            assert_eq!(expected_situation, &new_situation);
            Ok(())
        }

        #[test]
        fn test_simpleout() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "8");
            let mut expected_situation = situation.clone();
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_simpleout_oneout() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "8");
            situation.outs = 1;
            let mut expected_situation = situation.clone();
            expected_situation.outs = 2;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_simpleout_nextinning_top() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "8");
            situation.outs = 2;
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.inning.is_home = true;
            expected_situation.outs = 0;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_simpleout_nextinning_bottom() -> Result<()> {
            let (mut situation, play_line) = setup_with_inning(2, true, [false, true, false], "8");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.inning = Inning { number: 2, is_home: false };
            expected_situation.outs = 0;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_forceout() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "83");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_out_advance_first_second() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "8.1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_out_advance_second_third() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "8.2-3");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, true];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_out_advance_third_score() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, true], "8.3-H");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 1;
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_out_advance_second_third_score() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, true], "8.2-3;3-H");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, true];
            expected_situation.outs = 1;
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_out_advance_second_third_all_score() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, true], "8.2-H;3-H");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 1;
            expected_situation.cur_score_diff = 2;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_groundout_advance() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "54(B)/BG25/SH.1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_groundout_safe_and_score() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, true], "54(1)/FO/G5.3-H;B-1");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, false];
            expected_situation.outs = 1;
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_groundout_end_of_inning() -> Result<()> {
            // game BAL195704160, end of bottom of the 6th inning
            let (mut situation, play_line) = setup_with_inning(2, true, [true, true, true], "64(1)/FO");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 0;
            expected_situation.inning = Inning { number: 2, is_home: false};
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_groundout_batter_is_out() -> Result<()> {
            // game BAL195704270, top of the 5th inning
            let (mut situation, play_line) = setup_with_inning(1, false, [true, false, false], "14(1)/FO");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, false];
            expected_situation.outs = 2;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_forceout_duplicate_runners_but_three_outs() -> Result<()> {
            // game BAL195706220, bottom of the 8th inning
            let (mut situation, play_line) = setup_with_inning(2, false, [true, true, false], "35(2)/FO");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 0;
            expected_situation.inning.is_home = true;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_forceout_duplicate_runners_again_but_three_outs() -> Result<()> {
            // game BAL195708021, bottom of the 3th inning
            let (mut situation, play_line) = setup_with_inning(2, false, [true, true, false], "5(2)/FO");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 0;
            expected_situation.inning.is_home = true;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_forceout_batter_out_but_error_on_throw() -> Result<()> {
            // game DET196305050, bottom of the 4th inning
            let (mut situation, play_line) = setup_with_inning(1, true, [false, true, true], "5(B)5E2.2-3;3-H(NR)(UR)");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, true];
            expected_situation.outs = 2;
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_explicit_sacrifice() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "23/SH.1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_doubleplay() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "64(1)3/GDP/G6");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 2;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_doubleplay_lineout() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "8(B)84(2)/LDP/L8");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 2;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_doubleplay_lineout_unassisted() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "3(B)3(1)/LDP");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 2;
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
        fn test_single_no_fielder() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, false], "S");
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
        fn test_groundrule_double() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "DGR/L9LS.2-H");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_throwing_error() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "E1/TH/BG15.1-3");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, true];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_fielding_error() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "E3.1-2;B-1");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, true, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_fielders_choice_out_at_home() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, true], "FC5/G5.3XH(52)");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, false];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_fielders_choice_no_outs() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, true], "FC3/G3S.3-H;1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, true, false];
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_error_on_foul_ball() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "FLE5/P5F");
            let expected_situation = situation.clone();
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
        fn test_balk() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, true], "BK.3-H;1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_caught_stealing() -> Result<()> {
            let (mut situation, play_line) = setup([false, false, true], "CSH(12)");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_caught_stealing_advance() -> Result<()> {
            let (mut situation, play_line) = setup([true, true, false], "CS2(24).2-3");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, true];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_caught_stealing_error() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "CS2(2E4).1-3");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, true];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_defensive_indifference() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "DI.1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_other_advance() -> Result<()> {
            // "Thompson out trying to advance after ball eluded catcher"
            let (mut situation, play_line) = setup([false, true, false], "OA.2X3(25)");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
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
        fn test_pickoff() -> Result<()> {
            let (mut situation, play_line) = setup([false, true, false], "PO2(14)");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_pickoff_error() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "PO1(E3).1-2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_pickoff_caught_stealing() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "POCS2(14)");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, false, false];
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_stolen_base() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, false], "SB2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_stolen_base_multiple() -> Result<()> {
            let (mut situation, play_line) = setup([true, true, false], "SB2;SB3");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, true];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_stolen_base_multiple_home() -> Result<()> {
            let (mut situation, play_line) = setup([true, false, true], "SBH;SB2");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [false, true, false];
            expected_situation.cur_score_diff = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_weird_error_running() -> Result<()> {
            // game KCA200607040, bottom of the 3rd
            let (mut situation, play_line) = setup([true, true, true], "S7/L.3-H;2-H;1XH(7432/TH)(E7)");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, false, false];
            expected_situation.cur_score_diff = 2;
            expected_situation.outs = 1;
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_error_running() -> Result<()> {
            // game KCA200607210, bottom of the 3rd
            let (mut situation, play_line) = setup([true, false, false], "FC1.1X2(6E4);B-1");
            let mut expected_situation = situation.clone();
            expected_situation.runners = [true, true, false];
            assert_result(&expected_situation, &mut situation, &play_line)
        }

        #[test]
        fn test_putout_runner_at_wrong_base() -> Result<()> {
            // game DET196405140, bottom of the 4th
            let (mut situation, play_line) = setup([true, false, false], "36(1)/BF.B-1");
            let mut expected_situation = situation.clone();
            expected_situation.outs = 1;
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
