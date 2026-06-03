import { Redirect, type Href } from "expo-router";

export default function MainIndex() {
  return <Redirect href={"/(main)/chat" as Href} />;
}
