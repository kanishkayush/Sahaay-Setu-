const { z } = require('zod');
const { PartnerSearchResponseSchema } = require('./dist/partner.js');
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync('payload.json'));
try {
  PartnerSearchResponseSchema.parse(payload);
  console.log("SUCCESS");
} catch (e) {
  console.error("ERROR", e);
}
