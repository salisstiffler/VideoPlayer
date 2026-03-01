class Video {
  final String id;
  final String title;
  final String thumbnail;
  final String url;
  final String duration;
  final String site;

  Video({
    required this.id,
    required this.title,
    required this.thumbnail,
    required this.url,
    required this.duration,
    required this.site,
  });

  factory Video.fromJson(Map<String, dynamic> json) {
    return Video(
      id: json['id'] ?? '',
      title: json['title'] ?? '',
      thumbnail: json['thumbnail'] ?? '',
      url: json['url'] ?? '',
      duration: json['duration'] ?? '',
      site: json['site'] ?? '',
    );
  }
}

class Site {
  final String id;
  final String name;
  final String url;

  Site({required this.id, required this.name, required this.url});

  factory Site.fromJson(Map<String, dynamic> json) {
    return Site(
      id: json['id'] ?? '',
      name: json['name'] ?? '',
      url: json['url'] ?? '',
    );
  }
}

class AppVideoFormat {
  final String id;
  final String url;
  final String ext;
  final int height;
  final String note;
  final Map<String, String>? headers;

  AppVideoFormat({
    required this.id,
    required this.url,
    required this.ext,
    required this.height,
    required this.note,
    this.headers,
  });

  factory AppVideoFormat.fromJson(Map<String, dynamic> json) {
    return AppVideoFormat(
      id: json['id'] ?? '',
      url: json['url'] ?? '',
      ext: json['ext'] ?? '',
      height: json['height'] ?? 0,
      note: json['note'] ?? '',
      headers: json['headers'] != null ? Map<String, String>.from(json['headers']) : null,
    );
  }
}

class VideoDetail {
  final String title;
  final String thumbnail;
  final List<AppVideoFormat> formats;

  VideoDetail({
    required this.title,
    required this.thumbnail,
    required this.formats,
  });

  factory VideoDetail.fromJson(Map<String, dynamic> json) {
    var list = json['formats'] as List;
    List<AppVideoFormat> formatsList = list.map((i) => AppVideoFormat.fromJson(i)).toList();
    return VideoDetail(
      title: json['title'] ?? '',
      thumbnail: json['thumbnail'] ?? '',
      formats: formatsList,
    );
  }
}
