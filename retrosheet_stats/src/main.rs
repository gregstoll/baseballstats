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

// TODO - parallel

fn main() {
    println!("Hello, world!");
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_stub() {
        assert_eq!(0, 0);
    }
}