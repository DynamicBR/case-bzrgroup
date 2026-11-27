CREATE TABLE precatorio (
    id                    BIGSERIAL     PRIMARY KEY,
    numero_processo       CHAR(20)      NOT NULL UNIQUE,
    ente_devedor          TEXT          NOT NULL,
    valor_face            NUMERIC(15,2) NOT NULL CHECK (valor_face > 0),

    classificacao         TEXT          CHECK (classificacao IN ('alimentar', 'comum')),
    tipo_precatorio       TEXT          CHECK (tipo_precatorio IN ('federal', 'estadual', 'municipal')),

    apresentado_em        TIMESTAMPTZ,
    prazo_pagamento       DATE,

    saida_tribunal_em     TIMESTAMPTZ,
    chegada_operacao_em   TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE pagamento (
    id              BIGSERIAL     PRIMARY KEY,
    precatorio_id   BIGINT        NOT NULL REFERENCES precatorio (id),
    evento_id       TEXT          NOT NULL UNIQUE,
    tipo            TEXT          NOT NULL CHECK (tipo IN ('pagamento', 'estorno')),
    valor           NUMERIC(15,2) NOT NULL CHECK (valor > 0),
    pago_em         DATE          NOT NULL,
    atualizado_em   TIMESTAMPTZ   NOT NULL,
    criado_em       TIMESTAMPTZ   NOT NULL DEFAULT now()
);