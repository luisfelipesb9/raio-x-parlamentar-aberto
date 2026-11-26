"use client";

import { TIPOS_NO } from "@/lib/grafo";
import { FAMILIAS, type FamiliaRelacao } from "@/lib/grafo-mapa";
import { formataReais } from "@/lib/formato";
import { FormaGrupo, Forma } from "./FormaNo";
import { Termo } from "./Termo";

interface Props {
  /** Tipos de nó presentes na resposta, na ordem da legenda. */
  tipos: string[];
  /** Quantos nós de cada tipo aparecem no mapa agora (sem contar os que estão dentro de um grupo). */
  visiveis: ReadonlyMap<string, number>;
  /** Quantos nós de cada tipo a resposta trouxe. */
  totais: ReadonlyMap<string, number>;
  escondidos: ReadonlySet<string>;
  onAlternar: (tipo: string) => void;
  onLimpar: () => void;
  /** Quantas conexões de cada família estão visíveis. */
  familias: ReadonlyMap<FamiliaRelacao, number>;
  escala: { valor: number; tam: number }[];
}

/** Legenda viva: tipos de nó (filtro), famílias de ligação, escala de tamanho e sanção, com contagens do que está visível. */
export function GrafoLegenda({ tipos, visiveis, totais, escondidos, onAlternar, onLimpar, familias, escala }: Props) {
  return (
    <div className="legenda-viva">
      <ul className="legenda" aria-label="Legenda dos tipos de nó">
        {tipos.map((t) => {
          const ligado = !escondidos.has(t);
          return (
            <li key={t}>
              <button type="button" className="chip" aria-pressed={ligado} onClick={() => onAlternar(t)}>
                <Forma tipo={t} />
                <span>{TIPOS_NO[t]?.rotulo}</span>
                <small>
                  {visiveis.get(t) ?? 0} de {totais.get(t) ?? 0}
                </small>
              </button>
            </li>
          );
        })}
        <li className="chip-estatico">
          <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true" focusable="false">
            <rect x="3" y="3" width="12" height="12" fill="var(--no-empresa)" stroke="var(--perigo)" strokeWidth="3" />
          </svg>
          <span>
            Empresa com <Termo id="ceis-cnep">sanção</Termo>
          </span>
        </li>
        <li className="chip-estatico">
          <FormaGrupo />
          <span>
            <Termo id="grupo-nos">Grupo (+N)</Termo>: clique para abrir
          </span>
        </li>
      </ul>
      {escondidos.size > 0 && (
        <button type="button" className="btn btn-sec btn-mini" onClick={onLimpar}>
          Limpar filtros
        </button>
      )}

      <ul className="legenda legenda-linhas" aria-label="Cores das ligações">
        {(Object.keys(FAMILIAS) as FamiliaRelacao[]).map((f) => (
          <li key={f} title={FAMILIAS[f].ajuda}>
            <svg width="30" height="10" viewBox="0 0 30 10" aria-hidden="true" focusable="false">
              <line x1="1" y1="5" x2="29" y2="5" stroke={`var(${FAMILIAS[f].cor})`} strokeWidth={f === "dinheiro" ? 3.5 : 2} strokeLinecap="round" />
            </svg>
            <span>{FAMILIAS[f].rotulo}</span>
            <small>{familias.get(f) ?? 0}</small>
          </li>
        ))}
      </ul>

      <div className="legenda-escala">
        <Termo id="tamanho-espessura">Tamanho e espessura</Termo>:
        <span className="escala-circulos">
          {escala.length > 0 ? (
            [...escala].reverse().map((e) => (
              <span key={e.valor} className="escala-item">
                <svg width={e.tam + 2} height={e.tam + 2} viewBox={`0 0 ${e.tam + 2} ${e.tam + 2}`} aria-hidden="true" focusable="false">
                  <circle cx={(e.tam + 2) / 2} cy={(e.tam + 2) / 2} r={e.tam / 2} fill="var(--surface-2)" stroke="var(--fg)" strokeWidth="1.2" />
                </svg>
                <small>{formataReais(e.valor)}</small>
              </span>
            ))
          ) : (
            <small>nenhum valor em R$ neste mapa</small>
          )}
        </span>
        <small>maior = mais R$; linha mais grossa = valor maior. Linha tracejada ou pontilhada = certeza menor.</small>
      </div>
    </div>
  );
}
