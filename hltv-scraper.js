const HLTV = require('hltv').default;

async function getMatches() {
    try {
        // ALLE Matches holen (nicht nur live)
        const matches = await HLTV.getMatches();
        
        console.log("🔍 DEBUG: Total matches found:", matches.length);
        
        // Die ersten 6 Matches nehmen
        const recentMatches = matches.slice(0, 6);
        
        const simplifiedMatches = recentMatches.map(match => ({
            team1: match.team1?.name || 'TBA',
            team2: match.team2?.name || 'TBA',
            event: match.event?.name || 'Unknown Event',
            unix_time: Math.floor(Date.now() / 1000) + 3600, // +1 Stunde
            time_string: match.time || 'SOON'
        }));

        console.log(JSON.stringify(simplifiedMatches));
    } catch (error) {
        console.log("❌ HLTV Error:", error);
        console.log(JSON.stringify([]));
    }
}

getMatches();
