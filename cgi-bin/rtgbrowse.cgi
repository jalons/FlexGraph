#!/usr/bin/env ruby

require 'lib/gnuplotter'
require 'extractor/rtg'
require 'cgi'

$resourcePath = '/FlexGraph/'
$graphers = [
  { :regexp => /^CPU/, :plotter => 'cpuplot.cgi' },
  { :regexp => :default, :plotter => 'rtgplot.cgi' },
]

def aggrlink
  '<div id="aggrlink" style="display: none">
  <a href="#">View the aggregate of these graphs</a>
  </div>'
end

$title = nil
def title(t)
  $title = t
end

$body = []
def body(t)
  if t.kind_of?(Array)
    $body += t
  else
    $body << t
  end
end

def matches(description, routers)
    matches = []
    descr_split = description.split /\b/
    descr_split.each do |possibility|
      if routers.include? possibility
        matches << [ possibility, routers[possibility][:rid] ]
      end
    end
    return matches
end

cgi = CGI.new
rid = cgi.params['rid'][0].to_i
iid = cgi.params['iid'][0].to_i
old = cgi.params['old'][0].to_i

ex = RTGExtractor.new
routers = {}
ex.list_routers.each do |router|
  routers[router[:name]] = router
end

if !iid.nil? && iid != 0 && !rid.nil? && rid != 0
  # Display single interface with different time scales
  router = ex.router_name rid
  name, descr = ex.interface_name_descr(rid, iid)
  intf = [ name, descr ].join(" ")
  title router + ' - ' + intf

  # Get a list of routers that match this interface description
  see_also = matches(intf, routers).sort.map { |name, mrid| "<a href=?rid=#{mrid}>#{name}</a>" }
  
  # If we got matches, format them as links and present them
  if !see_also.empty?
    body "<div class='seealso'><p class='quiet'>See also:</p>"
    body "<p>" + see_also.join(", ") + "</p>"
    body "</div>"
  end

  [ 14400, 86400, 86400*7, 86400*30, 86400*365 ].each do |interval|
    body "<div class='interface'>"
    $graphers.each do |grapher|
      if grapher[:regexp] == :default || intf =~ grapher[:regexp]
        body "<a href='#{grapher[:plotter]}?w=1280&h=500&id=#{rid}:#{iid}&title=#{router}+#{intf}&secs=#{interval}&old=#{old}'>"
        body "<img src='#{grapher[:plotter]}?w=640&h=250&id=#{rid}:#{iid}&title=#{router}+#{intf}&secs=#{interval}&old=#{old}' />"
        body "</a>"
        break
      end
    end
    body "</div>"
  end
elsif !rid.nil? && rid != 0
  # Display all interfaces on a router
  router = ex.router_name rid
  title router

  # Sort the interface list as numerically as possible
  # i.e. GigabitEthernet1/0/2 before GigabitEthernet1/0/10
  intf_list = []
  ex.list_interfaces(rid).each do |intf|
    next if intf[:status] != 'active'
    next if intf[:speed] == 0
    # Remove extra spaces, add spaces between characters and numbers (i.e. Ethernet1 -> Ethernet 1)
    name_normalized = intf[:name].gsub(/\s+/, ' ').gsub(/([a-z])([0-9])/i, '\1 \2').gsub(/([0-9])([a-z])/i, '\1 \2')
    # Split on word boundaries into an array, and try to make numeric parts numeric
    name_split = name_normalized.split(/\b/).map { |x| (sprintf("%06d", x.to_i) if x =~ /^\d+$/) or x }
    intf_list << [ name_split, intf ]
  end
  intf_list.sort!

  body "<div id='aggrGraphs' style='display: none'>"
  body "<h2>Device Aggregate</h2>"
  ids = intf_list.map { |name, intf| rid.to_s + ':' + intf[:id].to_s }.join "+"
  body "<img width='620' height='200' data-src='rtgplot.cgi?w=620&h=200&id=#{ids}&title=Aggregate+traffic&secs=86400&old=#{old}&only_i=1' />"
  body "<img width='620' height='200' data-src='rtgplot.cgi?w=620&h=200&id=#{ids}&title=Aggregate+packets&secs=86400&old=#{old}&only_i=1&type=pps' />"
  body "</div>"

  body "<h2 class='hide'>Interfaces</h2>"

  body "<div class='hide'>"
  # Get list of routers that match any of the interface descriptions
  match_list = []
  intf_list.each do |s, i|
    match_list += matches(i[:description], routers)
  end

  # If we got matches, format them as links and present them
  if !match_list.empty?
    see_also = match_list.uniq.sort.map { |name, mrid| "<a href=?rid=#{mrid}>#{name}</a>" }
    body "<div class='seealso'><p class='quiet'>See also:</p>"
    body "<p>" + see_also.join(", ") + "</p>"
    body "</div>"
  end
  body "</div>"

  # Present each interface as an overview graph and a link to the full graph page
  intf_list.each do |intf_name_split, intf|
    body "<div class='interface filterable' id='#{intf[:name]} #{intf[:description]}'>"
    body "<a href='?rid=#{rid}&iid=#{intf[:id]}&old=#{old}'>"
    $graphers.each do |grapher|
      if grapher[:regexp] == :default || intf[:name] =~ grapher[:regexp]
        body "<img width='400' height='200' data-plot-id='#{rid}:#{intf[:id]}' src='#{grapher[:plotter]}?w=400&h=200&id=#{rid}:#{intf[:id]}&title=#{intf[:name]}+#{intf[:description]}&secs=43200&old=#{old}' />"
        break
      end
    end
    body "</a>"
    body "</div>"
  end
else
  # List all routers
  names = routers.keys.sort
  names.each do |name|
    router = routers[name]
    body "<div class='router filterable' id='#{name}'><a href='?rid=#{router[:rid]}&old=#{old}'>#{name}</a></div>"
  end
end

puts "Content-type: text/html\n\n"
puts <<HEADER
<!DOCTYPE html>
<html>
<head>
<link rel="stylesheet" href="#{$resourcePath}styles.css" />
<script type="text/javascript" src="http://ajax.googleapis.com/ajax/libs/jquery/1.5.2/jquery.min.js"></script>
<script type="text/javascript" src="#{$resourcePath}scripts.js"></script>
HEADER

if !$title.nil?
  puts "<title>#{$title}</title>"
else
  puts "<title>RTG Browser</title>"
end
puts "</head>"
puts "<body>"

puts "<div id='header'>"
puts "<span id='logo'>FlexGraph</span>"
puts "<span id='showAggr' style='display: none'><span class='separator'>|</span><input type='checkbox' id='aggrChecked'></input><label for='aggrChecked'>Show device aggregate graphs</label></span>"
puts "<span id='searchbox' style='display: none'><span class='separator'>|</span>Substring filter: <input type='text' name='search' id='search'></input></span>"
puts '</div>'

puts "<div id='content'>"

if !$title.nil?
  puts "<h1>#{$title}</h1>"
end

puts aggrlink
puts $body.join "\n"
puts "</div>"
puts "</body>"
puts "</html>"

