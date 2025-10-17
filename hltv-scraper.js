// hltv-scraper.js
const HLTV = require('hltv').default;

async function getMatches() {
    try {
        const matches = await HLTV.getLiveMatches();
        
        // Daten für Python aufbereiten
        const simplifiedMatches = matches.map(match => ({
            team1: match.team1?.name || 'TBA',
            team2: match.team2?.name || 'TBA',
            event: match.event?.name || 'Unknown Event',
            unix_time: Math.floor(Date.now() / 1000) + 3600, // +1h für Demo
            time_string: 'LIVE'
        }));

        console.log(JSON.stringify(simplifiedMatches));
    } catch (error) {
        console.log(JSON.stringify([]));
    }
}

getMatches();
