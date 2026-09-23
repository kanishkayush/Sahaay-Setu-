import fs from 'fs';
import { PartnerSearchResponseSchema } from './src/api/contracts/partner.ts';

const data = {
  items: JSON.parse(fs.readFileSync('../backend/data/channel_partners.json', 'utf8')),
  radiusKm: 25,
  fallbackUsed: false
};

const result = PartnerSearchResponseSchema.safeParse(data);
if (!result.success) {
  console.log(JSON.stringify(result.error.issues, null, 2));
} else {
  console.log("Success!");
}
