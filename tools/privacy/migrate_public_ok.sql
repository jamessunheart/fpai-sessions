-- d066 public/private lane migration.
-- Decisions remain private by default. Only rows James explicitly marks
-- public_ok = true may enter the public context pack.

ALTER TABLE brain_index.decisions
    ADD COLUMN IF NOT EXISTS public_ok BOOLEAN DEFAULT false;

UPDATE brain_index.decisions
   SET public_ok = false
 WHERE public_ok IS NULL;

ALTER TABLE brain_index.decisions
    ALTER COLUMN public_ok SET DEFAULT false;

