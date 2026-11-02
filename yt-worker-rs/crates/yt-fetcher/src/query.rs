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

/// Multi-Query Generator for travel, geography, and culinary culture shorts.
pub fn build_travel_queries(topic_title: &str, script_body: &str) -> Vec<String> {
    let mut queries = Vec::new();
    let text_lower = format!("{} {}", topic_title, script_body).to_lowercase();

    // 1. Food / Street Food Specifics
    if text_lower.contains("food") || text_lower.contains("taco") || text_lower.contains("pad thai") || text_lower.contains("market") {
        if text_lower.contains("bangkok") || text_lower.contains("thai") {
            queries.push("pad thai shrimp bangkok street food".to_string());
            queries.push("bangkok night market street food vendor".to_string());
            queries.push("yaowarat road chinatown bangkok night".to_string());
            queries.push("thai street food open flame wok".to_string());
            queries.push("tom yum kung thai soup street".to_string());
        }
        if text_lower.contains("mexico") || text_lower.contains("pastor") || text_lower.contains("taco") {
            queries.push("tacos al pastor trompo pineapple mexico city".to_string());
            queries.push("mexico city taqueria street tacos".to_string());
            queries.push("mexican street food plancha salsa cilantro".to_string());
            queries.push("carnitas copper cauldron traditional mexico".to_string());
            queries.push("mexico city night street food market".to_string());
        }
    }

    // 2. City & Landmark Queries
    queries.push(format!("{} landmarks architecture high quality", topic_title));
    queries.push(format!("{} authentic street photography", topic_title));
    queries.push(format!("{} aerial skyline evening", topic_title));
    queries.push(format!("{} cultural atmosphere travel documentary", topic_title));

    queries
}

/// Multi-Query Generator for history & documentary shorts.
pub fn build_history_queries(topic_title: &str, _script_body: &str) -> Vec<String> {
    let mut queries = Vec::new();
    queries.push(format!("{} historical photograph archival", topic_title));
    queries.push(format!("{} ancient ruins monument heritage", topic_title));
    queries.push(format!("{} museum artifact exhibition", topic_title));
    queries.push(format!("{} vintage portrait painting", topic_title));
    queries.push(format!("{} historical battle map documentary", topic_title));
    queries
}

/// Multi-Query Generator for science, space & tech shorts.
pub fn build_tech_queries(topic_title: &str, _script_body: &str) -> Vec<String> {
    let mut queries = Vec::new();
    queries.push(format!("{} aerospace rocket launchpad", topic_title));
    queries.push(format!("{} telescope space nebula observatory", topic_title));
    queries.push(format!("{} laboratory technology innovation", topic_title));
    queries.push(format!("{} microchip semiconductor hardware", topic_title));
    queries
}

/// Universal Category Query Dispatcher.
pub fn build_category_queries(category: &str, topic_title: &str, script_body: &str) -> Vec<String> {
    let cat = category.to_lowercase();
    if cat.contains("sport") || cat.contains("basketball") || cat.contains("nba") {
        build_sports_queries(topic_title, script_body)
    } else if cat.contains("travel") || cat.contains("gezi") || cat.contains("food") {
        build_travel_queries(topic_title, script_body)
    } else if cat.contains("history") || cat.contains("tarih") || cat.contains("war") {
        build_history_queries(topic_title, script_body)
    } else if cat.contains("tech") || cat.contains("science") || cat.contains("space") {
        build_tech_queries(topic_title, script_body)
    } else {
        let mut q = Vec::new();
        q.push(format!("{} documentary editorial photo", topic_title));
        q.push(format!("{} authentic photography high quality", topic_title));
        q.push(format!("{} cinematic realistic detail", topic_title));
        q
    }
}
