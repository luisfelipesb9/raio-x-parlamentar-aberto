"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { GrafoView } from "./GrafoView";
import { PickerDeputado } from "./Picker";

export function GrafoPagina() {
  const sp = useSearchParams();
  const router = useRouter();
  const centro = sp.get("centro");
  if (!centro) {
    return (
      <div className="pagina-estreita">
        <p className="lead">Escolha um deputado para ver, num mapa, com quem e com o quê ele se relaciona nos dados públicos.</p>
        <PickerDeputado onEscolher={(id) => router.push(`/grafo?centro=${encodeURIComponent(`deputado:${id}`)}`)} />
      </div>
    );
  }
  return <GrafoView key={centro} centro={centro} />;
}
