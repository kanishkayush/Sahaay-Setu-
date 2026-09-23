const fs = require('fs');
const { PartnerSearchResponseSchema } = require('./dist/partner.js');

const data = JSON.parse(fs.readFileSync('./partners_resp.json', 'utf8'));
const result = PartnerSearchResponseSchema.safeParse(data);
if (!result.success) {
  console.log(JSON.stringify(result.error.issues, null, 2));
} else {
  console.log("Success! Partners are valid now.");
}
