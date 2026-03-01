import 'dart:convert';
import 'package:http/http.dart' as http;
import '../models/video.dart';

class ApiService {
  static const String baseUrl = 'http://172.19.208.1:8000';

  static Future<List<Site>> getSites() async {
    final response = await http.get(Uri.parse('$baseUrl/sites'));
    if (response.statusCode == 200) {
      List<dynamic> body = json.decode(response.body);
      return body.map((dynamic item) => Site.fromJson(item)).toList();
    } else {
      throw Exception('Failed to load sites');
    }
  }

  static Future<List<Video>> getVideos(String siteId, int page) async {
    final response = await http.get(Uri.parse('$baseUrl/videos?site=$siteId&page=$page'));
    if (response.statusCode == 200) {
      List<dynamic> body = json.decode(response.body);
      return body.map((dynamic item) => Video.fromJson(item)).toList();
    } else {
      throw Exception('Failed to load videos');
    }
  }

  static Future<VideoDetail> getVideoDetail(String url) async {
    final response = await http.get(Uri.parse('$baseUrl/video_info?url=${Uri.encodeComponent(url)}'));
    if (response.statusCode == 200) {
      return VideoDetail.fromJson(json.decode(response.body));
    } else {
      throw Exception('Failed to load video details');
    }
  }
}
