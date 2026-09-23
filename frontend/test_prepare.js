const map = {
    '0': 'शून्य', '1': 'एक', '2': 'दो', '3': 'तीन', '4': 'चार',
    '5': 'पाँच', '6': 'छह', '7': 'सात', '8': 'आठ', '9': 'नौ'
};
function prepareTextForSpeech(text, language) {
  if (language !== 'hi') return text;
  return text.replace(/\d+/g, (match) => {
    if (match.length === 1) return map[match] ?? match;
    return match.split('').map(digit => map[digit] ?? digit).join(' ');
  });
}
console.log("TEST 1:", prepareTextForSpeech("कृपया अपना 6 अंकों का पिन कोड बताएं।", "hi"));
console.log("TEST 2:", prepareTextForSpeech("आपका पिन कोड 801503 दर्ज किया गया है।", "hi"));
console.log("TEST 3:", prepareTextForSpeech("5 लाख", "hi"));
console.log("TEST 4:", prepareTextForSpeech("6", "hi"));
