export function AvisoNaoAcusacao({ compacto = false }: { compacto?: boolean }) {
  return (
    <aside className={`aviso${compacto ? " aviso-compacto" : ""}`} aria-label="Aviso importante">
      <p>
        <strong>Isto não é acusação; é o que os dados públicos mostram.</strong>
        {!compacto && (
          <>
            {" "}
            Cada conclusão vem com um nível de certeza e com o caminho que o sistema percorreu, para você conferir nos documentos oficiais.
            Processo sem condenação definitiva não é culpa, e votação simbólica não é voto individual.
          </>
        )}
      </p>
    </aside>
  );
}
