#[macro_use] extern crate lazy_static;
extern crate regex;
use regex::Regex;

mod data {
    use std::collections::HashMap;

    #[derive(Debug, Clone, Copy, PartialEq, Eq, Hash)]
    pub enum RunnerInitialPosition {
        Batter,
        FirstBase,
        SecondBase,
        ThirdBase
    }

    #[derive(Debug, Clone, Copy, PartialEq, Eq)]
    pub enum RunnerFinalPosition {
        FirstBase,
        SecondBase,
        ThirdBase,
        HomePlate, // this means the runner scored
        StillAtBat, // only valid for Batter
        Undetermined
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
    }

}

enum Verbosity {
    Quiet = 0,
    Normal = 1,
    Verbose = 2
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
}
#[derive(Clone, Debug, PartialEq, Eq)]
struct PlayLineInfo<'a> {
    inning: u8,
    is_home: bool,
    player_id: &'a str,
    count_when_play_happened: &'a str,
    pitches_str: &'a str,
    play_str: &'a str
}

impl PlayLineInfo<'_> {
    fn new_from_line<'a>(line: &'a str) -> PlayLineInfo<'a> {
        lazy_static! {
            // TODO perf - opt out of unicode?
            static ref PLAY_RE : Regex = Regex::new(r"^play,\s?(\d+),\s?([01]),(.*?),(.*?),(.*?),(.*)$").unwrap();
        }
        let play_match = PLAY_RE.captures(line).unwrap();
        return PlayLineInfo {
            inning: play_match.get(1).unwrap().as_str().parse::<u8>().unwrap(),
            is_home: play_match.get(2).unwrap().as_str() == "1",
            player_id: play_match.get(3).unwrap().as_str(),
            count_when_play_happened: play_match.get(4).unwrap().as_str(),
            pitches_str: play_match.get(5).unwrap().as_str(),
            play_str: play_match.get(6).unwrap().as_str(),
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
            play_str: "HR/78/F"
        };
        assert_eq!(expected, play_line_info);
    }
}