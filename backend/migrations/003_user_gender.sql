BEGIN;

-- Contas antigas permanecem válidas: o preenchimento pode ser feito depois,
-- na tela de perfil.
ALTER TABLE users
    ADD COLUMN IF NOT EXISTS gender VARCHAR(20);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_users_gender_values'
    ) THEN
        ALTER TABLE users
            ADD CONSTRAINT ck_users_gender_values
            CHECK (gender IS NULL OR gender IN ('homem', 'mulher', 'nao_informado'));
    END IF;
END $$;

COMMIT;
