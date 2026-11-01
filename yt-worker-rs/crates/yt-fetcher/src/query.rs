/// Multi-Query Generator for sports shorts.
/// Generates 30-50 diverse action, celebration, and historical queries.
pub fn build_sports_queries(entity_name: &str, topic_title: &str) -> Vec<String> {
    let mut queries = Vec::new();
    let name = entity_name.trim();

    // 1. Core action shots
    queries.push(format!("\"{}\" dunk game action high quality", name));
    queries.push(format!("\"{}\" championship trophy celebration", name));
    queries.push(format!("\"{}\" clutch playoff game winner", name));
    queries.push(format!("\"{}\" defense block steal action", name));
    queries.push(format!("\"{}\" iconic photo shoot vintage", name));

    // 2. Career eras & specific teams
    if name.to_lowercase().contains("lebron") {
        queries.push("\"LeBron James\" Miami Heat 2012 2013 champions".to_string());
        queries.push("\"LeBron James\" Cleveland Cavaliers 2016 trophy".to_string());
        queries.push("\"LeBron James\" Los Angeles Lakers 2020 finals".to_string());
        queries.push("\"LeBron James\" chalk toss routine arena".to_string());
        queries.push("\"LeBron James\" high school St Vincent St Mary".to_string());
        queries.push("\"LeBron James\" Olympic gold medal Team USA".to_string());
        queries.push("\"LeBron James\" block on Andre Iguodala 2016".to_string());
    } else if name.to_lowercase().contains("wilt") {
        queries.push("\"Wilt Chamberlain\" 100 points game Hershey 1962".to_string());
        queries.push("\"Wilt Chamberlain\" vs Bill Russell Celtics duel".to_string());
        queries.push("\"Wilt Chamberlain\" Philadelphia Warriors dunk".to_string());
        queries.push("\"Wilt Chamberlain\" Los Angeles Lakers 1972 finals".to_string());
        queries.push("\"Wilt Chamberlain\" Harlem Globetrotters tour".to_string());
        queries.push("\"Wilt Chamberlain\" track and field high jump Kansas".to_string());
        queries.push("\"Wilt Chamberlain\" finger roll baseline layup".to_string());
    } else {
        queries.push(format!("\"{}\" rookie season action shot", name));
        queries.push(format!("\"{}\" all-star game MVP", name));
        queries.push(format!("\"{}\" finals MVP celebration", name));
    }

    // 3. Topic specific expansion
    queries.push(format!("{} {}", name, topic_title));

    queries
}
