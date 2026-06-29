import WidgetKit
import SwiftUI

private let appGroupId = "group.com.egoai.app.widget"
private let storageKey = "ego_mood_garden_widget_v1"

struct MoodGardenEntry: TimelineEntry {
  let date: Date
  let title: String
  let subtitle: String
  let emoji: String
  let goalsLine: String
  let atRisk: Bool
}

struct MoodGardenSnapshot: Decodable {
  let title: String
  let subtitle: String
  let emoji: String
  let goalsLine: String
  let atRisk: Bool
}

func loadMoodGardenEntry() -> MoodGardenEntry {
  let defaults = UserDefaults(suiteName: appGroupId)
  let json = defaults?.string(forKey: storageKey) ?? ""
  if let data = json.data(using: .utf8),
     let snap = try? JSONDecoder().decode(MoodGardenSnapshot.self, from: data) {
    return MoodGardenEntry(
      date: Date(),
      title: snap.title,
      subtitle: snap.subtitle,
      emoji: snap.emoji,
      goalsLine: snap.goalsLine,
      atRisk: snap.atRisk
    )
  }
  return MoodGardenEntry(
    date: Date(),
    title: "Jardim dos Monstrinhos",
    subtitle: "Abra o app para registrar seu humor",
    emoji: "🌱",
    goalsLine: "",
    atRisk: false
  )
}

struct MoodGardenProvider: TimelineProvider {
  func placeholder(in context: Context) -> MoodGardenEntry {
    loadMoodGardenEntry()
  }

  func getSnapshot(in context: Context, completion: @escaping (MoodGardenEntry) -> Void) {
    completion(loadMoodGardenEntry())
  }

  func getTimeline(in context: Context, completion: @escaping (Timeline<MoodGardenEntry>) -> Void) {
    let entry = loadMoodGardenEntry()
    let next = Calendar.current.date(byAdding: .minute, value: 30, to: Date()) ?? Date().addingTimeInterval(1800)
    completion(Timeline(entries: [entry], policy: .after(next)))
  }
}

struct MoodGardenWidgetView: View {
  var entry: MoodGardenEntry

  var body: some View {
    ZStack {
      if entry.atRisk {
        Color.orange.opacity(0.12)
      } else {
        Color.green.opacity(0.12)
      }
      HStack(alignment: .center, spacing: 10) {
        VStack(alignment: .leading, spacing: 4) {
          Text(entry.title)
            .font(.headline)
            .foregroundColor(.primary)
            .lineLimit(1)
          Text(entry.subtitle)
            .font(.caption)
            .foregroundColor(.secondary)
            .lineLimit(2)
          if !entry.goalsLine.isEmpty {
            Text(entry.goalsLine)
              .font(.caption2)
              .fontWeight(.semibold)
              .foregroundColor(.green)
          }
          if entry.atRisk {
            Text("Sequência em risco")
              .font(.caption2)
              .fontWeight(.bold)
              .foregroundColor(.orange)
          }
        }
        Spacer(minLength: 4)
        Text(entry.emoji)
          .font(.system(size: 34))
      }
      .padding(12)
    }
    .widgetURL(URL(string: "egoai://daily-care")!)
  }
}

@main
struct MoodGardenWidget: Widget {
  let kind: String = "MoodGardenWidget"

  var body: some WidgetConfiguration {
    StaticConfiguration(kind: kind, provider: MoodGardenProvider()) { entry in
      MoodGardenWidgetView(entry: entry)
    }
    .configurationDisplayName("Jardim dos Monstrinhos")
    .description("Humor, missões e sequência do jardim.")
    .supportedFamilies([.systemSmall, .systemMedium])
  }
}
