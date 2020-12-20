use std::fmt::Display;

enum Verbosity {
    Quiet = 0,
    Normal = 1,
    Verbose = 2
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
struct GameSituation {
    runners: [bool;3],
    inning: u8,
    cur_score_diff: i8,
    outs: u8, // TODO - should this be an enum?
    is_home: bool,
}

impl GameSituation {
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
}

// TODO - parallel

fn main() {
    println!("Hello, world!");
}

#[cfg(test)]
mod tests {
    #![allow(non_snake_case)]
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
}