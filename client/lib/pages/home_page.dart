import 'package:flutter/material.dart';
import '../models/video.dart';
import '../services/api_service.dart';
import 'video_list_page.dart';

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  late Future<List<Site>> _sitesFuture;

  // More professional gradients for TV
  final Map<String, List<Color>> _siteGradients = {
    'pornhub': [const Color(0xFFFF9900), const Color(0xFF282828)],
    'xvideos': [const Color(0xFFD00010), const Color(0xFF151515)],
    'xnxx': [const Color(0xFF151515), const Color(0xFFD00010)], // Reverse of XVideos or unique
    '51cg1': [const Color(0xFF0056B3), const Color(0xFF001F3F)],
    'jable': [const Color(0xFF007BFF), const Color(0xFF004085)],
    'missav': [const Color(0xFFE91E63), const Color(0xFF880E4F)],
    'youporn': [const Color(0xFFFF0066), const Color(0xFF000000)],
    'redtube': [const Color(0xFFD00010), const Color(0xFF000000)],
    'eporner': [const Color(0xFFAE0000), const Color(0xFF000000)],
    'porncom': [const Color(0xFF222222), const Color(0xFF000000)],
    'spankbang': [const Color(0xFFFF5500), const Color(0xFF000000)],
  };

  @override
  void initState() {
    super.initState();
    _sitesFuture = ApiService.getSites();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0A0A0A),
      body: Stack(
        children: [
          // Background subtle glow
          Positioned.fill(
            child: Container(
              decoration: BoxDecoration(
                gradient: RadialGradient(
                  center: Alignment.topLeft,
                  radius: 1.5,
                  colors: [
                    Colors.orange.withOpacity(0.05),
                    Colors.transparent,
                  ],
                ),
              ),
            ),
          ),
          CustomScrollView(
            slivers: [
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(48, 64, 48, 20),
                sliver: SliverToBoxAdapter(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'PornGemini',
                        style: TextStyle(
                          fontSize: 42,
                          fontWeight: FontWeight.w900,
                          letterSpacing: -1,
                          color: Colors.white,
                        ),
                      ),
                      Text(
                        'Choose your entertainment channel',
                        style: TextStyle(
                          fontSize: 18,
                          color: Colors.white.withOpacity(0.5),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              FutureBuilder<List<Site>>(
                future: _sitesFuture,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const SliverFillRemaining(
                      child: Center(child: CircularProgressIndicator(color: Colors.orange)),
                    );
                  }
                  
                  final sites = snapshot.data ?? [];
                  return SliverPadding(
                    padding: const EdgeInsets.symmetric(horizontal: 48, vertical: 20),
                    sliver: SliverGrid(
                      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                        crossAxisCount: 3,
                        crossAxisSpacing: 32,
                        mainAxisSpacing: 32,
                        childAspectRatio: 1.6, // Landscape ratio for TV
                      ),
                      delegate: SliverChildBuilderDelegate(
                        (context, index) {
                          final site = sites[index];
                          return _ChannelCard(
                            site: site,
                            gradient: _siteGradients[site.id] ?? [Colors.grey[900]!, Colors.black],
                            onTap: () {
                              Navigator.push(
                                context,
                                MaterialPageRoute(builder: (context) => VideoListPage(site: site)),
                              );
                            },
                          );
                        },
                        childCount: sites.length,
                      ),
                    ),
                  );
                },
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _ChannelCard extends StatefulWidget {
  final Site site;
  final List<Color> gradient;
  final VoidCallback onTap;

  const _ChannelCard({required this.site, required this.gradient, required this.onTap});

  @override
  State<_ChannelCard> createState() => _ChannelCardState();
}

class _ChannelCardState extends State<_ChannelCard> {
  bool _isFocused = false;

  @override
  Widget build(BuildContext context) {
    return Focus(
      onFocusChange: (focused) => setState(() => _isFocused = focused),
      child: GestureDetector(
        onTap: widget.onTap,
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          curve: Curves.easeOutCubic,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(20),
            gradient: LinearGradient(
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
              colors: _isFocused ? [widget.gradient[0], widget.gradient[0].withOpacity(0.6)] : widget.gradient,
            ),
            boxShadow: _isFocused
                ? [
                    BoxShadow(
                      color: widget.gradient[0].withOpacity(0.5),
                      blurRadius: 30,
                      spreadRadius: 5,
                    )
                  ]
                : [],
            border: Border.all(
              color: _isFocused ? Colors.white : Colors.white.withOpacity(0.1),
              width: _isFocused ? 4 : 1,
            ),
          ),
          child: ClipRRect(
            borderRadius: BorderRadius.circular(20),
            child: Stack(
              children: [
                // Glossy reflection effect when focused
                if (_isFocused)
                  Positioned(
                    top: -50,
                    left: -50,
                    child: Container(
                      width: 150,
                      height: 150,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Colors.white.withOpacity(0.1),
                      ),
                    ),
                  ),
                Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        widget.site.name.toUpperCase(),
                        style: TextStyle(
                          fontSize: 36,
                          fontWeight: FontWeight.w900,
                          color: Colors.white,
                          letterSpacing: 2,
                          shadows: [
                            Shadow(color: Colors.black.withOpacity(0.8), offset: const Offset(2, 2), blurRadius: 10),
                          ],
                        ),
                      ),
                      AnimatedOpacity(
                        duration: const Duration(milliseconds: 200),
                        opacity: _isFocused ? 1 : 0,
                        child: const Padding(
                          padding: EdgeInsets.only(top: 12.0),
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Icon(Icons.play_arrow_rounded, color: Colors.white, size: 24),
                              SizedBox(width: 4),
                              Text('ENTER CHANNEL', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 14)),
                            ],
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
