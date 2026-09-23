const fs = require('fs');
const { SchemeListResponseSchema } = require('./dist/scheme.js');

const data = JSON.parse(fs.readFileSync('../schemes_resp.json', 'utf8'));
const result = SchemeListResponseSchema.safeParse(data);
if (!result.success) {
  console.log(JSON.stringify(result.error.issues, null, 2));
} else {
  console.log("Success! Schemes are valid now.");
}
