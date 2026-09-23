import { SchemeListResponseSchema } from './src/api/contracts/schemes';
import fs from 'fs';

const data = JSON.parse(fs.readFileSync('schemes.json', 'utf8'));
const result = SchemeListResponseSchema.safeParse(data);
if (!result.success) {
  console.error(result.error);
} else {
  console.log("Success! Items:", result.data.items.length);
}
