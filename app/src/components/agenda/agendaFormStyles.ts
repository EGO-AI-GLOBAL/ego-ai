import { StyleSheet } from "react-native";

/** Estilos partilhados só do módulo agenda manual (não misturar com chat/voz). */
export const agendaFormStyles = StyleSheet.create({
  section: {
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginTop: 4,
    marginBottom: 10,
  },
  sectionInner: {
    fontSize: 11,
    fontWeight: "700",
    textTransform: "uppercase",
    letterSpacing: 0.6,
    marginTop: 8,
    marginBottom: 8,
  },
  muted: { fontSize: 14, lineHeight: 20, marginBottom: 8 },
  inviteInput: {
    borderWidth: 1,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 15,
    marginBottom: 8,
  },
  inviteBtn: {
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: "center",
    marginBottom: 4,
  },
  inviteBtnText: { color: "#fff", fontWeight: "800", fontSize: 15 },
  addBtn: {
    borderWidth: 1,
    borderRadius: 12,
    paddingVertical: 12,
    alignItems: "center",
    marginBottom: 10,
  },
  addBtnText: { fontSize: 15, fontWeight: "800" },
  formBox: {
    borderWidth: 1,
    borderRadius: 12,
    padding: 12,
    marginBottom: 12,
    gap: 8,
  },
  formLabel: { fontSize: 12, lineHeight: 16 },
  eventRowInputs: { flexDirection: "row", gap: 8 },
  eventDateInput: { flex: 1.4 },
  eventTimeInput: { flex: 0.8 },
});
