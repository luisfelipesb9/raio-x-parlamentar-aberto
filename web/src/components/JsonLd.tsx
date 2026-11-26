/** Dados estruturados (schema.org) em JSON-LD. O "<" é escapado para o conteúdo nunca fechar a tag <script>. */
export function JsonLd({ data }: { data: unknown }) {
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }} />;
}
