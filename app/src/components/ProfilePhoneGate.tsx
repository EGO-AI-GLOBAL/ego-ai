import React from "react";

type Props = {
  children: React.ReactNode;
};

/** Telefone já é pedido no signup; gate obrigatório removido. */
export function ProfilePhoneGate({ children }: Props) {
  return <>{children}</>;
}
