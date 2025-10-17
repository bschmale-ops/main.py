// hltv-scraper.js
const { getMatches } = require('hltv-api');

async function fetchMatches() {
    try {
        console.log("🔍 DEBUG: Trying dajk/hltv-api...");
        
        const matches = await getMatches();
        console.log("🔍 DEBUG: Total matches found:", matches.length);
        
        // Erste 6 Matches nehmen
        const recentMatches = matches.slice(0, 6);
        
        const simplifiedMatches = recentMatches.map(match => ({
            team1: match.team1 || 'TBA',
            team2: match.team2 || 'TBA',
            event: match.event || 'Unknown Event',
            unix_time: Math.floor(Date.now() / 1000) + 3600, // +1 Stunde
            time_string: 'SOON'
        }));

        console.log(JSON.stringify(simplifiedMatches));
    } catch (error) {
        console.log("❌ dajk/hltv-api Error:", error);
        console.log(JSON.stringify([]));
    }
}

fetchMatches();
